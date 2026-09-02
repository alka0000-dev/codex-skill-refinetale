変更案は、既存の `recordJobFinished` を唯一の完了計測点として維持し、呼び出し側では `finally` から1回だけ呼び出す形です。これにより成功・非同期失敗・同期 throw を同じ経路へ合流でき、duration の二重計測も避けられます。

## 変更契約

変更する挙動:

- `job_duration_seconds` を完了1件につき1回記録する
- duration は既存の `startedAt` と `finally` 内の終了時刻から算出する
- histogram label は `queue`、`region`、`outcome` のみ

変更しない挙動:

- `jobs_finished_total` の名前・label・記録回数
- `jobs_failed_total` の名前・label・`unknown` fallback
- `classifyFailure` による分類
- 例外の再throw
- ログの `durationMs`
- `jobName`、`accountId`、エラーメッセージはmetricsへ渡さない

## 型・instrument登録

```ts
const JOB_DURATION_BUCKETS_SECONDS = [0.1, 0.5, 1, 5, 15, 60] as const;

type JobOutcome = "success" | "failure";

const jobsFinished = meter.createCounter("jobs_finished_total");
const jobsFailed = meter.createCounter("jobs_failed_total");

const jobDuration = meter.createHistogram("job_duration_seconds", {
  unit: "s",
});
```

OpenTelemetry SDKのViewでbucketを登録します。以下は新しい `@opentelemetry/sdk-metrics` APIを使用する場合です。

```ts
import {
  AggregationType,
  MeterProvider,
  View,
} from "@opentelemetry/sdk-metrics";

const meterProvider = new MeterProvider({
  views: [
    new View({
      instrumentName: "job_duration_seconds",
      aggregation: {
        type: AggregationType.EXPLICIT_BUCKET_HISTOGRAM,
        options: {
          boundaries: [...JOB_DURATION_BUCKETS_SECONDS],
        },
      },
    }),
  ],
  // 既存のresource/readers設定はそのまま
});
```

Viewはinstrument生成前にMeterProviderへ登録します。`createHistogram` の `advice` はSDKが無視できるヒントなので、bucketを要件として保証するならViewを正本にします。

## 記録処理

```ts
type QueueName = "critical" | "default" | "bulk";
type Region = "ap-northeast-1" | "us-east-1";
type FailureReason = "timeout" | "dependency" | "invalid_input" | "unknown";

type JobContext = {
  queue: QueueName;
  region: Region;
  jobName: string;
  accountId: string;
};

function baseJobLabels(ctx: JobContext) {
  return { queue: ctx.queue, region: ctx.region } as const;
}

export function recordJobFinished(input: {
  ctx: JobContext;
  outcome: JobOutcome;
  durationMs: number;
  reason?: FailureReason;
}) {
  const completionLabels = {
    ...baseJobLabels(input.ctx),
    outcome: input.outcome,
  } as const;

  jobsFinished.add(1, completionLabels);

  if (input.outcome === "failure") {
    jobsFailed.add(1, {
      ...baseJobLabels(input.ctx),
      reason: input.reason ?? "unknown",
    });
  }

  jobDuration.record(input.durationMs / 1_000, completionLabels);
}
```

秒変換をここに置くことで、histogramのunitと変換責務が同じ場所に保たれます。`completionLabels` はcounterとhistogramで共有しますが、failure counterは従来どおり `outcome` ではなく `reason` を持ちます。

## 呼び出し側

```ts
const startedAt = monotonicClock.nowMs();
let completion: {
  outcome: JobOutcome;
  reason?: FailureReason;
} = {
  outcome: "success",
};

try {
  await handler.run(job);
} catch (error) {
  completion = {
    outcome: "failure",
    reason: classifyFailure(error),
  };
  throw error;
} finally {
  const durationMs = monotonicClock.nowMs() - startedAt;

  recordJobFinished({
    ctx,
    ...completion,
    durationMs,
  });

  logger.info({ durationMs }, "job finished");
}
```

`await handler.run(job)` は関数呼び出し自体も `try` 内で評価されるため、Promiseを返す前の同期 throw も `catch` されます。`throw error` の後にも `finally` が必ず実行されるので、failureとして1回記録してから同じ例外を再throwします。

durationを表す変数は `durationMs` だけです。同じ値をmetricsとログへ渡し、追加timerやwall clockは導入しません。

## 必要なテスト

### 記録処理

```ts
it("successのcounterとdurationを同じ低カーディナリティlabelで記録する", () => {
  recordJobFinished({
    ctx,
    outcome: "success",
    durationMs: 1_250,
  });

  expect(jobsFinished.add).toHaveBeenCalledTimes(1);
  expect(jobsFinished.add).toHaveBeenCalledWith(1, {
    queue: "critical",
    region: "ap-northeast-1",
    outcome: "success",
  });
  expect(jobsFailed.add).not.toHaveBeenCalled();
  expect(jobDuration.record).toHaveBeenCalledTimes(1);
  expect(jobDuration.record).toHaveBeenCalledWith(1.25, {
    queue: "critical",
    region: "ap-northeast-1",
    outcome: "success",
  });
});

it("failureの既存reason分類を維持してdurationを1回記録する", () => {
  recordJobFinished({
    ctx,
    outcome: "failure",
    reason: "timeout",
    durationMs: 500,
  });

  expect(jobsFinished.add).toHaveBeenCalledWith(1, {
    queue: "critical",
    region: "ap-northeast-1",
    outcome: "failure",
  });
  expect(jobsFailed.add).toHaveBeenCalledWith(1, {
    queue: "critical",
    region: "ap-northeast-1",
    reason: "timeout",
  });
  expect(jobDuration.record).toHaveBeenCalledTimes(1);
  expect(jobDuration.record).toHaveBeenCalledWith(0.5, {
    queue: "critical",
    region: "ap-northeast-1",
    outcome: "failure",
  });
});

it("reason未指定時のunknown fallbackを維持する", () => {
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
```

各metrics呼び出しのlabelを完全一致で検証するため、`jobName`、`accountId`、error messageの混入も検出できます。

### 実行経路

呼び出し側のテストでは最低限、次の3経路を確認します。

| 経路 | 期待するoutcome | observation | 例外 |
|---|---|---:|---|
| 正常完了 | `success` | 1回 | なし |
| Promise reject | `failure` | 1回 | 同じ例外を再throw |
| 同期 throw | `failure` | 1回 | 同じ例外を再throw |

同期 throw の中心的な検証例です。

```ts
it("handler.runの同期throwをfailureとして1回計測し再throwする", async () => {
  const error = new Error("failed");

  monotonicClock.nowMs
    .mockReturnValueOnce(1_000)
    .mockReturnValueOnce(2_500);

  handler.run.mockImplementation(() => {
    throw error;
  });
  classifyFailure.mockReturnValue("dependency");

  await expect(runJob(job, ctx)).rejects.toBe(error);

  expect(recordJobFinished).toHaveBeenCalledTimes(1);
  expect(recordJobFinished).toHaveBeenCalledWith({
    ctx,
    outcome: "failure",
    reason: "dependency",
    durationMs: 1_500,
  });
  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 1_500 },
    "job finished",
  );
});
```

bucketについては、`InMemoryMetricExporter` などで収集したhistogramの明示境界が `[0.1, 0.5, 1, 5, 15, 60]` であることをMeterProviderの結合テスト1件で確認します。

作業ディレクトリに実装対象やテスト環境がなく書き込みもできなかったため、上記テストは未実行です。実プロジェクトへ適用する際は、使用中の `@opentelemetry/sdk-metrics` バージョンに合わせてView登録構文だけ確認する必要があります。
