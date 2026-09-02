提案は、終了処理を1つの `finally` に集約し、既存の `durationMs` をログとhistogramで共有する形です。追加timer・wall clock・終了時刻の再取得は不要です。

## 変更契約

変更する挙動：

- `job_duration_seconds` をunit `s`、境界 `[0.1, 0.5, 1, 5, 15, 60]` で登録する。
- 成功・失敗とも、完了した1 jobにつき1回だけ観測する。
- histogramのlabelは `queue`、`region`、`outcome` のみ。

変更しない挙動：

- `jobs_finished_total`、`jobs_failed_total` の名前とlabel。
- `FailureReason` と `classifyFailure` の分類。
- 失敗時の例外再throw。
- ログの `durationMs`。
- monotonic clockを開始・終了の2回だけ読むこと。

## 型・登録・記録処理

以下は、利用中のOpenTelemetry Metrics APIが `advice.explicitBucketBoundaries` をサポートする前提です。プロジェクトがSDK Viewでbucketを管理している場合は、同じ境界を既存View側の正本へ設定し、両方へ重複定義しません。

```ts
const jobsFinished = meter.createCounter("jobs_finished_total");
const jobsFailed = meter.createCounter("jobs_failed_total");

const jobDuration = meter.createHistogram("job_duration_seconds", {
  unit: "s",
  advice: {
    explicitBucketBoundaries: [0.1, 0.5, 1, 5, 15, 60],
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

function baseJobLabels(ctx: JobContext) {
  return {
    queue: ctx.queue,
    region: ctx.region,
  } as const;
}

export function recordJobFinished(input: {
  ctx: JobContext;
  outcome: JobOutcome;
  durationMs: number;
  reason?: FailureReason;
}) {
  const labels = {
    ...baseJobLabels(input.ctx),
    outcome: input.outcome,
  };

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

`durationMs` を入力の正本にする理由は、monotonic clockと既存ログがmillisecondsだからです。secondsへの変換は、unitを所有するhistogram記録境界で一度だけ行います。

`labels` に入るのは型・実値ともに `queue`、`region`、`outcome` だけです。`ctx` 自体をspreadしないため、`jobName` や `accountId` が混入しません。errorも記録関数へ渡しません。

## 呼び出し側

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

これにより：

- `handler.run(job)` が同期的にthrowしても `catch` される。
- `outcome` と `reason` を確定した後、成功・失敗とも同じ終了経路へ合流する。
- `recordJobFinished` は構造上1か所からしか呼ばれず、histogramも1回だけ記録される。
- `nowMs()` は開始時と `finally` の計2回だけ。
- 再throwする値は従来どおり元の `error`。
- 失敗時だけ既存の `jobsFailed` 分岐が実行される。

## 最小テスト

登録テスト：

```ts
it("registers job duration histogram in seconds with bounded buckets", () => {
  expect(meter.createHistogram).toHaveBeenCalledWith(
    "job_duration_seconds",
    {
      unit: "s",
      advice: {
        explicitBucketBoundaries: [0.1, 0.5, 1, 5, 15, 60],
      },
    },
  );
});
```

成功経路：

```ts
it("records one successful completion using the existing clock pair", async () => {
  monotonicClock.nowMs
    .mockReturnValueOnce(1_000)
    .mockReturnValueOnce(2_500);
  handler.run.mockResolvedValue(undefined);

  await runJob();

  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);

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
  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 1_500 },
    "job finished",
  );
});
```

同期throwと非同期rejectは同じ不変条件を共有するため、表形式にできます。

```ts
it.each([
  [
    "synchronous throw",
    () => {
      throw jobError;
    },
  ],
  [
    "asynchronous rejection",
    () => Promise.reject(jobError),
  ],
])(
  "records one failed completion for %s and rethrows",
  async (_case, implementation) => {
    monotonicClock.nowMs
      .mockReturnValueOnce(1_000)
      .mockReturnValueOnce(1_600);
    handler.run.mockImplementationOnce(implementation);
    classifyFailure.mockReturnValue("dependency");

    await expect(runJob()).rejects.toBe(jobError);

    expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);

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

    expect(classifyFailure).toHaveBeenCalledWith(jobError);
  },
);
```

`toHaveBeenCalledWith` のlabel完全一致が、`jobName`、`accountId`、error messageを含まないことの実行時証拠になります。

作業ディレクトリには実装ファイルやテスト環境がなく、かつ読み取り専用だったため、コード変更・ビルド・lint・テスト実行はしていません。実プロジェクトでは上記3系統のテストに加え、SDKのexport結果で指定bucketが実際に採用されていることを1件確認すれば、登録から出力まで検証できます。
