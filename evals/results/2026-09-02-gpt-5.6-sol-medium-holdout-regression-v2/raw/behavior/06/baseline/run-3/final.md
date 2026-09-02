以下の形なら、既存の完了計測点を維持しつつ、成功・失敗とも1ジョブにつき1回だけhistogramへ記録できます。

## 1. メトリクス登録と型

OpenTelemetryでは秒のunitをUCUM表記の `"s"` とし、bucketはSDKのViewで設定します。以下は `@opentelemetry/sdk-metrics` 2.x向けです。[OpenTelemetry JS Metrics](https://github.com/open-telemetry/opentelemetry-js/blob/main/doc/metrics.md)

```ts
// telemetry.ts
import {
  AggregationType,
  InstrumentType,
  MeterProvider,
  createAllowListAttributesProcessor,
} from "@opentelemetry/sdk-metrics";

export const meterProvider = new MeterProvider({
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

      // 記録処理の誤変更に対する防御。SDK 2.xで利用可能。
      attributesProcessors: [
        createAllowListAttributesProcessor([
          "queue",
          "region",
          "outcome",
        ]),
      ],
    },
  ],
});
```

SDK 1.xを使用中なら、同じ境界値を `new View()` と `new ExplicitBucketHistogramAggregation()` で設定します。2.xではこれらのclassが廃止されています。[OpenTelemetry JS 2.x移行ガイド](https://github.com/open-telemetry/opentelemetry-js/blob/main/doc/upgrade-to-2.x.md)

既存metricsモジュールにはhistogramと必須のduration入力を追加します。

```ts
const jobsFinished = meter.createCounter("jobs_finished_total");
const jobsFailed = meter.createCounter("jobs_failed_total");

const jobDuration = meter.createHistogram("job_duration_seconds", {
  description: "Duration of completed jobs",
  unit: "s",
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
  return {
    queue: ctx.queue,
    region: ctx.region,
  } as const;
}

function jobDurationLabels(ctx: JobContext, outcome: JobOutcome) {
  return {
    ...baseJobLabels(ctx),
    outcome,
  } as const;
}

export function recordJobFinished(input: RecordJobFinishedInput) {
  jobsFinished.add(1, {
    ...baseJobLabels(input.ctx),
    outcome: input.outcome,
  });

  if (input.outcome === "failure") {
    jobsFailed.add(1, {
      ...baseJobLabels(input.ctx),
      reason: input.reason ?? "unknown",
    });
  }

  jobDuration.record(
    input.durationSeconds,
    jobDurationLabels(input.ctx, input.outcome),
  );
}
```

`durationSeconds` を必須にすることで、counterだけ記録してhistogramを忘れる呼び出しを型エラーにできます。`jobName`、`accountId`、`reason`をhistogram用label関数へ渡さないため、高カーディナリティ化も防げます。

## 2. 呼び出し側

完了記録を`finally`へ一元化します。monotonic clockは開始時と完了時の2回だけ読み、その差をログとhistogramで共用します。

```ts
const startedAtMs = monotonicClock.nowMs();

let outcome: JobOutcome = "failure";
let failureReason: FailureReason | undefined;

try {
  await handler.run(job);
  outcome = "success";
} catch (error) {
  failureReason = classifyFailure(error);
  throw error;
} finally {
  const durationMs = monotonicClock.nowMs() - startedAtMs;

  recordJobFinished({
    ctx,
    outcome,
    reason: failureReason,
    durationSeconds: durationMs / 1_000,
  });

  logger.info({ durationMs }, "job finished");
}
```

`handler.run(job)`の呼び出し自体が同期throwしても、式の評価が`try`内なので`catch`されます。その後`finally`でfailureとして一度だけ記録され、元の例外が再throwされます。

また、メトリクス記録をログより先に置くことで、loggerが例外を投げても完了計測が欠落しません。これは既存の実行順序とも一致します。

## 3. Jestテスト

最低限、以下を仕様として固定します。

```ts
describe("recordJobFinished", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("成功したjobのcounterとdurationを許可されたlabelだけで1回記録する", () => {
    recordJobFinished({
      ctx: {
        queue: "critical",
        region: "ap-northeast-1",
        jobName: "send-notification",
        accountId: "account-123",
      },
      outcome: "success",
      durationSeconds: 0.75,
    });

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

  it("失敗したjobの既存counterとdurationをそれぞれ1回記録する", () => {
    recordJobFinished({
      ctx: {
        queue: "bulk",
        region: "us-east-1",
        jobName: "import-customers",
        accountId: "account-456",
      },
      outcome: "failure",
      reason: "timeout",
      durationSeconds: 15.25,
    });

    expect(jobsFinished.add).toHaveBeenCalledWith(1, {
      queue: "bulk",
      region: "us-east-1",
      outcome: "failure",
    });
    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: "bulk",
      region: "us-east-1",
      reason: "timeout",
    });

    expect(jobDuration.record).toHaveBeenCalledTimes(1);
    expect(jobDuration.record).toHaveBeenCalledWith(15.25, {
      queue: "bulk",
      region: "us-east-1",
      outcome: "failure",
    });
  });

  it("failure reason省略時も既存どおりunknownを記録する", () => {
    recordJobFinished({
      ctx,
      outcome: "failure",
      durationSeconds: 1,
    });

    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: ctx.queue,
      region: ctx.region,
      reason: "unknown",
    });
  });
});
```

実行処理については、同期throwとclockの読み取り回数を明示的に検証します。

```ts
it("handlerが同期throwしてもfailure durationを1回記録して同じ例外を再throwする", async () => {
  const error = new Error("handler failed");

  handler.run.mockImplementation(() => {
    throw error;
  });
  monotonicClock.nowMs
    .mockReturnValueOnce(1_000)
    .mockReturnValueOnce(2_500);
  classifyFailure.mockReturnValue("dependency");

  await expect(runJob(job, ctx)).rejects.toBe(error);

  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
  expect(classifyFailure).toHaveBeenCalledWith(error);
  expect(recordJobFinished).toHaveBeenCalledTimes(1);
  expect(recordJobFinished).toHaveBeenCalledWith({
    ctx,
    outcome: "failure",
    reason: "dependency",
    durationSeconds: 1.5,
  });
  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 1_500 },
    "job finished",
  );
});
```

加えて、SDK設定テストまたはInMemory exporterによる結合テストで、境界値が厳密に `[0.1, 0.5, 1, 5, 15, 60]` になっていることを1ケース固定すると、Viewの設定漏れを検出できます。

この案では新しい抽象化を増やさず、既存の「完了記録」「基底label」「failure reason分類」をそのまま正本として利用しています。実リポジトリが提示されていないため、コード実行・lint・型チェックは未実施です。
