`recordJobFinished` を唯一の完了計測点として維持し、durationを必須引数に追加します。呼び出し側では成功・失敗分岐内の記録をやめ、`finally` で既存の終了時刻を1回だけ取得して記録します。

### 1. 型とinstrument登録

OpenTelemetryのunitはUCUM表記の `"s"` を使用します。

```ts
const jobDurationBucketsSeconds = [0.1, 0.5, 1, 5, 15, 60];

const jobsFinished = meter.createCounter("jobs_finished_total");
const jobsFailed = meter.createCounter("jobs_failed_total");

const jobDuration = meter.createHistogram("job_duration_seconds", {
  unit: "s",
  advice: {
    explicitBucketBoundaries: jobDurationBucketsSeconds,
  },
});

type QueueName = "critical" | "default" | "bulk";
type Region = "ap-northeast-1" | "us-east-1";
type FailureReason =
  | "timeout"
  | "dependency"
  | "invalid_input"
  | "unknown";
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
  durationSeconds: number;
  reason?: FailureReason;
};

function baseJobLabels(ctx: JobContext) {
  return { queue: ctx.queue, region: ctx.region } as const;
}
```

`advice.explicitBucketBoundaries` よりSDK側のView設定が優先される構成なら、Viewにも同じ境界値を設定します。既存Viewがこのinstrumentを別のbucketへ上書きしていないことも確認対象です。

### 2. 完了メトリクスの記録

histogramのlabelは専用に組み立てます。`ctx` 全体を展開しないため、将来 `JobContext` にフィールドが追加されても高カーディナリティlabelへ流入しません。

```ts
export function recordJobFinished(input: RecordJobFinishedInput) {
  const baseLabels = baseJobLabels(input.ctx);

  jobsFinished.add(1, {
    ...baseLabels,
    outcome: input.outcome,
  });

  if (input.outcome === "failure") {
    jobsFailed.add(1, {
      ...baseLabels,
      reason: input.reason ?? "unknown",
    });
  }

  jobDuration.record(input.durationSeconds, {
    ...baseLabels,
    outcome: input.outcome,
  });
}
```

これにより既存counterは変更されません。

- `jobs_finished_total`: `queue`, `region`, `outcome`
- `jobs_failed_total`: `queue`, `region`, `reason`
- `job_duration_seconds`: `queue`, `region`, `outcome`

`jobName`、`accountId`、error message、`reason` はhistogramへ入りません。

### 3. 呼び出し側

終了時刻は既存の `finally` で1回だけ取得します。成功時・失敗時に個別に `recordJobFinished` を呼ばないことが二重計測防止の要点です。

```ts
const startedAt = monotonicClock.nowMs();

let outcome: JobOutcome = "failure";
let failureReason: FailureReason | undefined;

try {
  await handler.run(job);
  outcome = "success";
} catch (error) {
  failureReason = classifyFailure(error);
  throw error;
} finally {
  const durationMs = monotonicClock.nowMs() - startedAt;

  recordJobFinished({
    ctx,
    outcome,
    reason: failureReason,
    durationSeconds: durationMs / 1_000,
  });

  logger.info({ durationMs }, "job finished");
}
```

`handler.run(job)` がPromiseを返す前に同期throwしても、`catch` を通って以下が成立します。

- `outcome` は `failure`
- `classifyFailure` は従来どおり実行
- `finally` で1回だけ計測
- 元の例外オブジェクトを再throw
- `nowMs()` は開始・終了の合計2回だけ
- ログとhistogramは同じ `durationMs` に由来

### 4. Jestテスト

既存のinstrument mockへ `jobDuration.record` を追加します。

```ts
describe("recordJobFinished", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("成功したjobのcounterとdurationを許可されたlabelで1回記録する", () => {
    const ctx: JobContext = {
      queue: "critical",
      region: "ap-northeast-1",
      jobName: "send-email",
      accountId: "account-123",
    };

    recordJobFinished({
      ctx,
      outcome: "success",
      durationSeconds: 0.75,
    });

    expect(jobsFinished.add).toHaveBeenCalledTimes(1);
    expect(jobsFinished.add).toHaveBeenCalledWith(1, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "success",
    });

    expect(jobsFailed.add).not.toHaveBeenCalled();

    expect(jobDuration.record).toHaveBeenCalledTimes(1);
    expect(jobDuration.record).toHaveBeenCalledWith(0.75, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "success",
    });
  });

  it("失敗したjobのcounterとdurationをそれぞれ1回記録する", () => {
    const ctx: JobContext = {
      queue: "bulk",
      region: "us-east-1",
      jobName: "import-data",
      accountId: "account-456",
    };

    recordJobFinished({
      ctx,
      outcome: "failure",
      reason: "dependency",
      durationSeconds: 5.25,
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
      reason: "dependency",
    });

    expect(jobDuration.record).toHaveBeenCalledTimes(1);
    expect(jobDuration.record).toHaveBeenCalledWith(5.25, {
      queue: "bulk",
      region: "us-east-1",
      outcome: "failure",
    });
  });

  it("失敗理由がない場合も既存どおりunknownで記録する", () => {
    recordJobFinished({
      ctx: {
        queue: "default",
        region: "ap-northeast-1",
        jobName: "cleanup",
        accountId: "account-789",
      },
      outcome: "failure",
      durationSeconds: 1,
    });

    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: "default",
      region: "ap-northeast-1",
      reason: "unknown",
    });
  });
});
```

呼び出し側では同期throwと時計の呼び出し回数を固定します。以下の `runJob` は先ほどの `try/catch/finally` を含む関数を指します。

```ts
it("handlerが同期throwしてもfailureを1回計測して同じ例外を再throwする", async () => {
  const error = new Error("handler failed");

  monotonicClock.nowMs
    .mockReturnValueOnce(10_000)
    .mockReturnValueOnce(10_750);

  handler.run.mockImplementation(() => {
    throw error;
  });
  classifyFailure.mockReturnValue("dependency");

  await expect(runJob()).rejects.toBe(error);

  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
  expect(classifyFailure).toHaveBeenCalledTimes(1);
  expect(classifyFailure).toHaveBeenCalledWith(error);

  expect(recordJobFinished).toHaveBeenCalledTimes(1);
  expect(recordJobFinished).toHaveBeenCalledWith({
    ctx,
    outcome: "failure",
    reason: "dependency",
    durationSeconds: 0.75,
  });

  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 750 },
    "job finished",
  );
});
```

登録設定もテスト可能なら固定します。

```ts
expect(meter.createHistogram).toHaveBeenCalledWith(
  "job_duration_seconds",
  {
    unit: "s",
    advice: {
      explicitBucketBoundaries: [0.1, 0.5, 1, 5, 15, 60],
    },
  },
);
```

実リポジトリが提示されていないため、ビルド・lint・テスト実行は未実施です。また、`referytale` が要求する事前対応表は、作業領域が読み取り専用のためファイル保存できませんでした。
