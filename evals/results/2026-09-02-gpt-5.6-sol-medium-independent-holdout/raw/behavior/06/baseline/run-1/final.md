変更の中心は、既存の `recordJobFinished` を唯一の完了計測点として維持し、呼び出し側で算出した `durationMs` を渡すことです。これにより、counterとhistogramが同じ完了事象から記録され、二重計測を避けられます。

前提として OpenTelemetry JS の `advice.explicitBucketBoundaries` を利用できるバージョンを想定します。

### 型とinstrument登録

```ts
const JOB_DURATION_BUCKETS_SECONDS = [0.1, 0.5, 1, 5, 15, 60] as const;

const jobsFinished = meter.createCounter("jobs_finished_total");
const jobsFailed = meter.createCounter("jobs_failed_total");

const jobDurationSeconds = meter.createHistogram("job_duration_seconds", {
  description: "Duration of completed jobs",
  unit: "s",
  advice: {
    explicitBucketBoundaries: [...JOB_DURATION_BUCKETS_SECONDS],
  },
});

type QueueName = "critical" | "default" | "bulk";
type Region = "ap-northeast-1" | "us-east-1";
type FailureReason =
  | "timeout"
  | "dependency"
  | "invalid_input"
  | "unknown";

type JobContext = {
  queue: QueueName;
  region: Region;
  jobName: string;
  accountId: string;
};

type JobCompletion =
  | {
      outcome: "success";
      reason?: never;
    }
  | {
      outcome: "failure";
      reason?: FailureReason;
    };

type RecordJobFinishedInput = {
  ctx: JobContext;
  durationMs: number;
} & JobCompletion;

function baseJobLabels(ctx: JobContext) {
  return {
    queue: ctx.queue,
    region: ctx.region,
  } as const;
}
```

`unit` はOpenTelemetryの単位表記に合わせて `"s"` とします。値もミリ秒から秒へ変換して記録します。

### 記録処理

```ts
export function recordJobFinished(input: RecordJobFinishedInput): void {
  const completionLabels = {
    ...baseJobLabels(input.ctx),
    outcome: input.outcome,
  } as const;

  // 既存counterの名前・labelを維持する。
  jobsFinished.add(1, completionLabels);

  if (input.outcome === "failure") {
    jobsFailed.add(1, {
      ...baseJobLabels(input.ctx),
      reason: input.reason ?? "unknown",
    });
  }

  // 完了したjobごとに、この計測点で一度だけ記録する。
  jobDurationSeconds.record(input.durationMs / 1_000, completionLabels);
}
```

histogramへ渡すlabelは `queue`、`region`、`outcome` のみです。`JobContext` 全体をspreadしないため、`jobName` や `accountId` が将来誤って入ることも防げます。

### 呼び出し側

終了時刻を `finally` で一度だけ取得し、その値をmetricsと既存ログの両方に使います。

```ts
const startedAt = monotonicClock.nowMs();

let outcome: "success" | "failure" = "success";
let failureReason: FailureReason | undefined;

try {
  await handler.run(job);
} catch (error) {
  outcome = "failure";
  failureReason = classifyFailure(error);
  throw error;
} finally {
  const durationMs = monotonicClock.nowMs() - startedAt;

  if (outcome === "success") {
    recordJobFinished({
      ctx,
      outcome,
      durationMs,
    });
  } else {
    recordJobFinished({
      ctx,
      outcome,
      reason: failureReason,
      durationMs,
    });
  }

  logger.info({ durationMs }, "job finished");
}
```

この構造では次が保証されます。

- `nowMs()` は開始時と終了時の計2回だけ
- metricsとログが同じ `durationMs` を利用
- 成功・失敗ともhistogramは1回
- `handler.run(job)` の同期throwも `catch` される
- 元の例外をそのまま再throw
- `classifyFailure` の既存分類を変更しない

### 記録処理のテスト

```ts
describe("recordJobFinished", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("successのcounterとdurationを許可されたlabelだけで記録する", () => {
    recordJobFinished({
      ctx: {
        queue: "critical",
        region: "ap-northeast-1",
        jobName: "send-email",
        accountId: "account-123",
      },
      outcome: "success",
      durationMs: 1_500,
    });

    expect(jobsFinished.add).toHaveBeenCalledTimes(1);
    expect(jobsFinished.add).toHaveBeenCalledWith(1, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "success",
    });

    expect(jobsFailed.add).not.toHaveBeenCalled();

    expect(jobDurationSeconds.record).toHaveBeenCalledTimes(1);
    expect(jobDurationSeconds.record).toHaveBeenCalledWith(1.5, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "success",
    });
  });

  test("failureの既存counterとdurationをそれぞれ1回記録する", () => {
    recordJobFinished({
      ctx: {
        queue: "bulk",
        region: "us-east-1",
        jobName: "import-data",
        accountId: "account-456",
      },
      outcome: "failure",
      reason: "dependency",
      durationMs: 500,
    });

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

    expect(jobDurationSeconds.record).toHaveBeenCalledTimes(1);
    expect(jobDurationSeconds.record).toHaveBeenCalledWith(0.5, {
      queue: "bulk",
      region: "us-east-1",
      outcome: "failure",
    });
  });

  test("failure reason未指定時は既存どおりunknownを使う", () => {
    recordJobFinished({
      ctx,
      outcome: "failure",
      durationMs: 100,
    });

    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: ctx.queue,
      region: ctx.region,
      reason: "unknown",
    });
  });
});
```

### 実行処理のテスト

実際には呼び出し部分を関数としてテストします。以下では仮に `executeJob` としています。

```ts
describe("executeJob", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("成功時に同じmonotonic durationをmetricとログへ渡す", async () => {
    monotonicClock.nowMs
      .mockReturnValueOnce(1_000)
      .mockReturnValueOnce(2_500);

    handler.run.mockResolvedValue(undefined);

    await executeJob(job, ctx);

    expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
    expect(recordJobFinished).toHaveBeenCalledTimes(1);
    expect(recordJobFinished).toHaveBeenCalledWith({
      ctx,
      outcome: "success",
      durationMs: 1_500,
    });
    expect(logger.info).toHaveBeenCalledWith(
      { durationMs: 1_500 },
      "job finished",
    );
  });

  test("同期throwをfailureとして1回計測し、同じ例外を再throwする", async () => {
    const originalError = new Error("synchronous failure");

    monotonicClock.nowMs
      .mockReturnValueOnce(10_000)
      .mockReturnValueOnce(10_500);

    handler.run.mockImplementation(() => {
      throw originalError;
    });
    classifyFailure.mockReturnValue("dependency");

    await expect(executeJob(job, ctx)).rejects.toBe(originalError);

    expect(classifyFailure).toHaveBeenCalledTimes(1);
    expect(classifyFailure).toHaveBeenCalledWith(originalError);
    expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);

    expect(recordJobFinished).toHaveBeenCalledTimes(1);
    expect(recordJobFinished).toHaveBeenCalledWith({
      ctx,
      outcome: "failure",
      reason: "dependency",
      durationMs: 500,
    });
  });

  test("非同期rejectもfailureとして1回計測して再throwする", async () => {
    const originalError = new Error("asynchronous failure");

    monotonicClock.nowMs
      .mockReturnValueOnce(2_000)
      .mockReturnValueOnce(7_000);

    handler.run.mockRejectedValue(originalError);
    classifyFailure.mockReturnValue("timeout");

    await expect(executeJob(job, ctx)).rejects.toBe(originalError);

    expect(recordJobFinished).toHaveBeenCalledTimes(1);
    expect(recordJobFinished).toHaveBeenCalledWith({
      ctx,
      outcome: "failure",
      reason: "timeout",
      durationMs: 5_000,
    });
  });
});
```

instrument登録もテスト可能なら、次を固定すると要件の後退を検知できます。

```ts
expect(meter.createHistogram).toHaveBeenCalledWith(
  "job_duration_seconds",
  expect.objectContaining({
    unit: "s",
    advice: {
      explicitBucketBoundaries: [0.1, 0.5, 1, 5, 15, 60],
    },
  }),
);
```

なお、利用中のOpenTelemetry SDKが `advice` を未サポート、またはViewで集約設定を上書きしている場合は、同じ境界をSDK側の明示的なHistogram Viewにも設定する必要があります。今回の案では、指示対象と役割を先に分ける方針に従い、「経過時間の算出は呼び出し側」「完了metricsの記録は既存関数」に責務を分離しています。
