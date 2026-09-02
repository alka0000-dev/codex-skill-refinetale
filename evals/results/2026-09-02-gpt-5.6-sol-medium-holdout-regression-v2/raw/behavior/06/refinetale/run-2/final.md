変更案の中心は、`recordJobFinished` を「ジョブ完了メトリクスの唯一の記録点」にし、呼び出し側の `finally` から1回だけ呼ぶことです。これにより、counter と histogram の二重計測や経路ごとの記録漏れを構造的に防げます。

作業ディレクトリには実装・テストが存在しなかったため、以下は提示コードを正本とした具体案です。

## 変更契約

変更する挙動:

- `job_duration_seconds` histogramを追加する。
- 成功・失敗とも完了した1ジョブにつき1回、秒単位で記録する。
- bucket境界を `[0.1, 0.5, 1, 5, 15, 60]` にする。
- `recordJobFinished` がcounterとdurationの両方を所有する。

変更しない挙動:

- `jobs_finished_total` と `jobs_failed_total` の名前・labelを維持する。
- failure reasonの分類と、未指定時の `"unknown"` fallbackを維持する。
- `handler.run` の例外は同じ例外を再throwする。
- ログの `durationMs` と計測位置を維持する。
- `jobName`、`accountId`、エラーメッセージをmetric labelへ渡さない。

共通処理:

- 成否にかかわらず、終了時刻を1回取得する。
- 同じ`durationMs`をログとhistogramへ使用する。
- `jobsFinished`とhistogramを1回ずつ記録する。

差分処理:

- failure時だけ`jobsFailed`を記録する。
- failure時だけ`FailureReason`を保持する。

## 型・記録処理

```ts
const jobsFinished = meter.createCounter("jobs_finished_total");
const jobsFailed = meter.createCounter("jobs_failed_total");

const jobDuration = meter.createHistogram("job_duration_seconds", {
  unit: "s",
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
  return { queue: ctx.queue, region: ctx.region } as const;
}

export function recordJobFinished(input: RecordJobFinishedInput) {
  const completionLabels = {
    ...baseJobLabels(input.ctx),
    outcome: input.outcome,
  };

  jobsFinished.add(1, completionLabels);
  jobDuration.record(input.durationMs / 1_000, completionLabels);

  if (input.outcome === "failure") {
    jobsFailed.add(1, {
      ...baseJobLabels(input.ctx),
      reason: input.reason ?? "unknown",
    });
  }
}
```

`completionLabels`がhistogramと既存finished counterの共通表現です。`JobContext`自体をspreadしないため、`jobName`と`accountId`はlabel経路へ入りません。エラーも`recordJobFinished`に渡さず、分類済みの`FailureReason`だけを渡します。

## bucket登録

OpenTelemetry JS 2.xでは、bucketをSDK側のViewで確定させます。

```ts
import {
  AggregationType,
  InstrumentType,
  MeterProvider,
} from "@opentelemetry/sdk-metrics";

const meterProvider = new MeterProvider({
  views: [
    {
      instrumentName: "job_duration_seconds",
      instrumentType: InstrumentType.HISTOGRAM,
      aggregation: {
        type: AggregationType.EXPLICIT_BUCKET_HISTOGRAM,
        options: {
          boundaries: [0.1, 0.5, 1, 5, 15, 60],
        },
      },
    },
  ],
});
```

bucketをinstrumentの`advice.explicitBucketBoundaries`にも重複定義しません。Viewをbucket設定の正本にすることで、値の不一致を避けます。OpenTelemetry公式ドキュメントでも、明示bucketはViewのexplicit histogram aggregationで設定されています。[OpenTelemetry JS metrics documentation](https://github.com/open-telemetry/opentelemetry-js/blob/main/doc/metrics.md)

この構文は`@opentelemetry/sdk-metrics` 2.x前提です。1.xではViewの構築APIだけが異なるため、実際の`package.json`確認後に登録部分のみ合わせる必要があります。[OpenTelemetry JS 2.x migration guide](https://github.com/open-telemetry/opentelemetry-js/blob/main/doc/upgrade-to-2.x.md)

## 呼び出し側

```ts
const startedAt = monotonicClock.nowMs();

let completion: JobCompletion = {
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

  try {
    recordJobFinished({
      ctx,
      durationMs,
      ...completion,
    });
  } finally {
    logger.info({ durationMs }, "job finished");
  }
}
```

重要な点は次の3つです。

- `nowMs()`は開始時と終了時の計2回だけです。
- `recordJobFinished`の呼び出しは`finally`内の1か所だけです。
- `await handler.run(job)`は、同期throwとPromise rejectの両方を同じ`catch`でfailureにします。

内側の`try/finally`は、メトリクス記録が例外を投げた場合にも既存どおり終了ログを実行するためのものです。

## 必要なテスト

### `recordJobFinished`

```ts
it("successをcounterとhistogramへ1回記録する", () => {
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

  expect(jobDuration.record).toHaveBeenCalledTimes(1);
  expect(jobDuration.record).toHaveBeenCalledWith(1.25, {
    queue: "critical",
    region: "ap-northeast-1",
    outcome: "success",
  });

  expect(jobsFailed.add).not.toHaveBeenCalled();
});
```

```ts
it("failureを各metricへ1回記録し、既存reasonを維持する", () => {
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

  expect(jobDuration.record).toHaveBeenCalledWith(0.5, {
    queue: "critical",
    region: "ap-northeast-1",
    outcome: "failure",
  });

  expect(jobsFailed.add).toHaveBeenCalledWith(1, {
    queue: "critical",
    region: "ap-northeast-1",
    reason: "timeout",
  });
});
```

```ts
it("reason未指定のfailureをunknownとして記録する", () => {
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

完全一致でlabelを検証するため、`jobName`、`accountId`、error messageの混入も同時に検出できます。

### ジョブ実行経路

最低限、以下の3経路をジョブ実行処理のテストで保証します。

| 経路 | 期待結果 |
|---|---|
| 正常終了 | successで1回記録、同じ`durationMs`をログにも使用 |
| Promise reject | failureで1回記録、分類済みreason、同じ例外を再throw |
| 同期throw | failureで1回記録、分類済みreason、同じ例外を再throw |

同期throwの中心的なテストは次の形です。

```ts
it("handlerの同期throwをfailureとして1回記録し、同じ例外を再throwする", async () => {
  const error = new Error("failed");

  monotonicClock.nowMs
    .mockReturnValueOnce(10_000)
    .mockReturnValueOnce(10_500);

  handler.run.mockImplementation(() => {
    throw error;
  });

  await expect(runJob(job, ctx)).rejects.toBe(error);

  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
  expect(recordJobFinished).toHaveBeenCalledTimes(1);
  expect(recordJobFinished).toHaveBeenCalledWith({
    ctx,
    outcome: "failure",
    reason: "dependency",
    durationMs: 500,
  });
  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 500 },
    "job finished",
  );
});
```

bucketはmockではなく、`InMemoryMetricExporter`で1件記録して、出力されたhistogramの境界が`[0.1, 0.5, 1, 5, 15, 60]`になっていることをSDK統合テストで1件確認します。

実リポジトリが空だったため、これらのテスト・ビルド・lintは未実施です。実装時にはOpenTelemetryの導入バージョンと既存`MeterProvider`の所有箇所を確認し、そこへViewを1つ追加するのが最小変更です。
