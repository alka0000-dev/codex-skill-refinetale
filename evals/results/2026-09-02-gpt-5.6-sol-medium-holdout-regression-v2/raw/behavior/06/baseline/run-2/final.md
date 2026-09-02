変更の要点は、既存の `recordJobFinished` を唯一の完了メトリクス記録点として維持し、呼び出し側では終了時刻を `finally` で一度だけ取得することです。

`outcome` と `reason` を先に確定してから、counterとhistogramをまとめて1回記録します。

### 型・instrument登録・記録処理

```ts
const JOB_DURATION_BUCKETS_SECONDS = [0.1, 0.5, 1, 5, 15, 60];

const jobsFinished = meter.createCounter("jobs_finished_total");
const jobsFailed = meter.createCounter("jobs_failed_total");

const jobDurationSeconds = meter.createHistogram("job_duration_seconds", {
  // OpenTelemetryのunitはUCUM表記。
  unit: "s",
  advice: {
    explicitBucketBoundaries: JOB_DURATION_BUCKETS_SECONDS,
  },
});

type QueueName = "critical" | "default" | "bulk";
type Region = "ap-northeast-1" | "us-east-1";
type FailureReason = "timeout" | "dependency" | "invalid_input" | "unknown";
type JobOutcome = "success" | "failure";

type JobContext = {
  queue: QueueName;
  region: Region;
  jobName: string;
  accountId: string;
};

type RecordJobFinishedInput = {
  ctx: JobContext;
  outcome: JobOutcome;
  reason?: FailureReason;
  durationSeconds: number;
};

function baseJobLabels(ctx: JobContext) {
  return { queue: ctx.queue, region: ctx.region } as const;
}

export function recordJobFinished(input: RecordJobFinishedInput) {
  const completionLabels = {
    ...baseJobLabels(input.ctx),
    outcome: input.outcome,
  } as const;

  // 既存counterの名前とlabelsは変更しない。
  jobsFinished.add(1, completionLabels);

  if (input.outcome === "failure") {
    jobsFailed.add(1, {
      ...baseJobLabels(input.ctx),
      reason: input.reason ?? "unknown",
    });
  }

  // 完了メトリクス記録1回につき、observationも1回。
  jobDurationSeconds.record(input.durationSeconds, completionLabels);
}
```

`unit: "s"` はOpenTelemetryのUCUM表記で「seconds」を意味します。

なお、`advice.explicitBucketBoundaries` をサポートしないOpenTelemetry JSバージョンを使用している場合は、同じ境界値をSDK側の `View` で設定します。既存の `View` がある場合はinstrument側のadviceより優先される可能性があるため、`job_duration_seconds` に競合する設定がないことも確認対象です。

### 呼び出し側

```ts
const startedAtMs = monotonicClock.nowMs();

let outcome: JobOutcome = "success";
let failureReason: FailureReason | undefined;

try {
  await handler.run(job);
} catch (error) {
  outcome = "failure";
  failureReason = classifyFailure(error);
  throw error;
} finally {
  const finishedAtMs = monotonicClock.nowMs();
  const durationMs = finishedAtMs - startedAtMs;

  recordJobFinished({
    ctx,
    outcome,
    reason: failureReason,
    durationSeconds: durationMs / 1_000,
  });

  logger.info({ durationMs }, "job finished");
}
```

この構造により、次が保証されます。

- `nowMs()` は開始・終了の1組だけ
- loggerとhistogramは同じ差分値を使用
- 成功・失敗とも `recordJobFinished` は1回
- `handler.run(job)` の同期throwも `catch` される
- 捕捉した例外は従来どおり再throw
- `jobName`、`accountId`、error messageはlabelsに入らない

### メトリクス単体テスト

以下ではinstrumentをmock済みとします。

```ts
describe("recordJobFinished", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("成功したジョブのcounterと所要時間を同じ低カーディナリティlabelsで1回記録する", () => {
    const ctx: JobContext = {
      queue: "critical",
      region: "ap-northeast-1",
      jobName: "send-email",
      accountId: "account-123",
    };

    recordJobFinished({
      ctx,
      outcome: "success",
      durationSeconds: 1.25,
    });

    const expectedLabels = {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "success",
    };

    expect(jobsFinished.add).toHaveBeenCalledTimes(1);
    expect(jobsFinished.add).toHaveBeenCalledWith(1, expectedLabels);

    expect(jobsFailed.add).not.toHaveBeenCalled();

    expect(jobDurationSeconds.record).toHaveBeenCalledTimes(1);
    expect(jobDurationSeconds.record).toHaveBeenCalledWith(
      1.25,
      expectedLabels,
    );
  });

  it("失敗したジョブのfailure counterと所要時間をそれぞれ1回記録する", () => {
    const ctx: JobContext = {
      queue: "bulk",
      region: "us-east-1",
      jobName: "import-data",
      accountId: "account-456",
    };

    recordJobFinished({
      ctx,
      outcome: "failure",
      reason: "timeout",
      durationSeconds: 15,
    });

    expect(jobsFinished.add).toHaveBeenCalledTimes(1);
    expect(jobsFinished.add).toHaveBeenCalledWith(1, {
      queue: "bulk",
      region: "us-east-1",
      outcome: "failure",
    });

    expect(jobsFailed.add).toHaveBeenCalledTimes(1);
    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: "bulk",
      region: "us-east-1",
      reason: "timeout",
    });

    expect(jobDurationSeconds.record).toHaveBeenCalledTimes(1);
    expect(jobDurationSeconds.record).toHaveBeenCalledWith(15, {
      queue: "bulk",
      region: "us-east-1",
      outcome: "failure",
    });
  });

  it("失敗理由が省略された場合は既存どおりunknownを記録する", () => {
    recordJobFinished({
      ctx: {
        queue: "default",
        region: "ap-northeast-1",
        jobName: "cleanup",
        accountId: "account-789",
      },
      outcome: "failure",
      durationSeconds: 0.5,
    });

    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: "default",
      region: "ap-northeast-1",
      reason: "unknown",
    });
  });
});
```

完全一致でlabelsを検証しているため、`jobName` や `accountId` が誤って追加された場合もテストが失敗します。

### 呼び出し側の同期throwテスト

呼び出し処理を `executeJob` のような関数としてテストできる前提です。

```ts
it("handlerが同期的にthrowしてもfailureを1回記録して同じ例外を再throwする", async () => {
  const error = new Error("handler failed");

  monotonicClock.nowMs
    .mockReturnValueOnce(10_000)
    .mockReturnValueOnce(12_500);

  handler.run.mockImplementation(() => {
    throw error;
  });

  classifyFailure.mockReturnValue("dependency");

  await expect(executeJob(job, ctx)).rejects.toBe(error);

  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
  expect(classifyFailure).toHaveBeenCalledWith(error);

  expect(recordJobFinished).toHaveBeenCalledTimes(1);
  expect(recordJobFinished).toHaveBeenCalledWith({
    ctx,
    outcome: "failure",
    reason: "dependency",
    durationSeconds: 2.5,
  });

  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 2_500 },
    "job finished",
  );
});
```

成功経路にも、同様に以下を検証するテストを置きます。

```ts
expect(recordJobFinished).toHaveBeenCalledTimes(1);
expect(recordJobFinished).toHaveBeenCalledWith({
  ctx,
  outcome: "success",
  reason: undefined,
  durationSeconds: 2.5,
});
```

最重要の回帰防止点は、instrument登録時のbucket設定、labelsの完全一致、`recordJobFinished` と `histogram.record` の呼び出し回数、monotonic clockが開始・終了の2回だけ呼ばれることです。
