完了時の処理を `finally` に集約し、終了時刻を1回だけ取得するのが安全です。これにより成功・失敗・同期throwのすべてで、1ジョブにつき1回だけhistogramへ記録できます。

### メトリクス定義と型

```ts
const JOB_DURATION_BUCKETS_SECONDS = [0.1, 0.5, 1, 5, 15, 60];

const jobsFinished = meter.createCounter("jobs_finished_total");
const jobsFailed = meter.createCounter("jobs_failed_total");

const jobDuration = meter.createHistogram("job_duration_seconds", {
  unit: "s",
  advice: {
    explicitBucketBoundaries: JOB_DURATION_BUCKETS_SECONDS,
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
  reason?: FailureReason;
  durationMs: number;
};

type JobFinishedLabels = {
  queue: QueueName;
  region: Region;
  outcome: JobOutcome;
};

function baseJobLabels(ctx: JobContext) {
  return { queue: ctx.queue, region: ctx.region } as const;
}

function jobFinishedLabels(
  ctx: JobContext,
  outcome: JobOutcome,
): JobFinishedLabels {
  return {
    ...baseJobLabels(ctx),
    outcome,
  };
}
```

OpenTelemetryのunitはUCUM表記の `"s"` がsecondsを意味します。利用中のOpenTelemetry SDKで `advice.explicitBucketBoundaries` が未対応、またはSDK側にViewが設定されている場合は、同じ境界値をSDKのViewに設定してください。既存Viewがあればそちらが優先される可能性があります。

### 記録処理

```ts
export function recordJobFinished(input: RecordJobFinishedInput): void {
  const labels = jobFinishedLabels(input.ctx, input.outcome);

  jobsFinished.add(1, labels);

  jobDuration.record(input.durationMs / 1_000, labels);

  if (input.outcome === "failure") {
    jobsFailed.add(1, {
      ...baseJobLabels(input.ctx),
      reason: input.reason ?? "unknown",
    });
  }
}
```

重要なのは、histogram用ラベルを呼び出し側から受け取らず、この関数内で組み立てる点です。`jobName`、`accountId`、error messageが入り込む経路を作りません。

histogramのラベル組み合わせは最大で以下の12通りです。

```text
3 queue × 2 region × 2 outcome = 12
```

既存counterについては名前・ラベル・failure reason分類を変更していません。

### 呼び出し側

```ts
const startedAt = monotonicClock.nowMs();

let outcome: JobOutcome = "success";
let reason: FailureReason | undefined;

try {
  await handler.run(job);
} catch (error) {
  outcome = "failure";
  reason = classifyFailure(error);
  throw error;
} finally {
  const durationMs = monotonicClock.nowMs() - startedAt;

  recordJobFinished({
    ctx,
    outcome,
    reason,
    durationMs,
  });

  logger.info({ durationMs }, "job finished");
}
```

この構造には次の性質があります。

- `monotonicClock.nowMs()` は開始と終了の計2回だけ
- loggerとhistogramは同じ `durationMs` を使用
- `recordJobFinished` の呼び出しは `finally` の1か所だけ
- `handler.run()` の同期throwも `catch` される
- failure reasonを分類してから従来どおり再throw
- 成功・失敗ともhistogramへ1回だけ記録

### Jestテスト案

メトリクス記録関数では、値、回数、ラベルの完全一致を検証します。

```ts
describe("recordJobFinished", () => {
  const ctx: JobContext = {
    queue: "critical",
    region: "ap-northeast-1",
    jobName: "send-invoice",
    accountId: "account-123",
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("成功したジョブの所要時間をsecondsへ変換して1回記録する", () => {
    recordJobFinished({
      ctx,
      outcome: "success",
      durationMs: 1_500,
    });

    expect(jobsFinished.add).toHaveBeenCalledTimes(1);
    expect(jobsFinished.add).toHaveBeenCalledWith(1, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "success",
    });

    expect(jobDuration.record).toHaveBeenCalledTimes(1);
    expect(jobDuration.record).toHaveBeenCalledWith(1.5, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "success",
    });

    expect(jobsFailed.add).not.toHaveBeenCalled();
  });

  it("失敗したジョブの所要時間と既存failure counterをそれぞれ1回記録する", () => {
    recordJobFinished({
      ctx,
      outcome: "failure",
      reason: "dependency",
      durationMs: 600,
    });

    expect(jobsFinished.add).toHaveBeenCalledTimes(1);
    expect(jobsFinished.add).toHaveBeenCalledWith(1, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "failure",
    });

    expect(jobDuration.record).toHaveBeenCalledTimes(1);
    expect(jobDuration.record).toHaveBeenCalledWith(0.6, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "failure",
    });

    expect(jobsFailed.add).toHaveBeenCalledTimes(1);
    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: "critical",
      region: "ap-northeast-1",
      reason: "dependency",
    });
  });

  it("failure reasonがない場合は既存どおりunknownを使用する", () => {
    recordJobFinished({
      ctx,
      outcome: "failure",
      durationMs: 100,
    });

    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: "critical",
      region: "ap-northeast-1",
      reason: "unknown",
    });
  });
});
```

呼び出し側では、同期throw、再throw、時計の呼び出し回数を検証します。

```ts
it("handlerが同期的にthrowしてもfailureとして1回計測し同じ例外を再throwする", async () => {
  const error = new Error("synchronous failure");

  monotonicClock.nowMs
    .mockReturnValueOnce(1_000)
    .mockReturnValueOnce(1_600);

  handler.run.mockImplementation(() => {
    throw error;
  });

  classifyFailure.mockReturnValue("dependency");

  await expect(runJob(job, ctx)).rejects.toBe(error);

  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
  expect(classifyFailure).toHaveBeenCalledWith(error);

  expect(recordJobFinished).toHaveBeenCalledTimes(1);
  expect(recordJobFinished).toHaveBeenCalledWith({
    ctx,
    outcome: "failure",
    reason: "dependency",
    durationMs: 600,
  });

  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 600 },
    "job finished",
  );
});

it("handlerが完了した場合はsuccessとして1回計測する", async () => {
  monotonicClock.nowMs
    .mockReturnValueOnce(2_000)
    .mockReturnValueOnce(2_500);

  handler.run.mockResolvedValue(undefined);

  await runJob(job, ctx);

  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
  expect(recordJobFinished).toHaveBeenCalledTimes(1);
  expect(recordJobFinished).toHaveBeenCalledWith({
    ctx,
    outcome: "success",
    reason: undefined,
    durationMs: 500,
  });
});
```

さらに登録テストまたはSDK統合テストで、`job_duration_seconds`、unit `"s"`、指定した6境界が実際に適用されることを確認すれば、Viewによるbucket上書きも検出できます。

今回はコードベースが提示されておらず環境も読み取り専用だったため、実ファイルへの適用やテスト実行は行っていません。
