変更の中心は、成功・失敗を先に確定し、既存monotonic clockの終了値を`finally`で一度だけ取得して、counterとhistogramを同じ`recordJobFinished`呼び出しで記録することです。

前提として、OpenTelemetry JSの`advice.explicitBucketBoundaries`を利用できるバージョンを想定します。unitの「seconds」はOpenTelemetryの正規表現である`"s"`を指定します。

### 型・登録・記録処理

```ts
import type { Meter } from "@opentelemetry/api";

const JOB_DURATION_BUCKETS_SECONDS = [0.1, 0.5, 1, 5, 15, 60];

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
  durationSeconds: number;
} & JobCompletion;

function baseJobLabels(ctx: JobContext) {
  return {
    queue: ctx.queue,
    region: ctx.region,
  } as const;
}

export function registerJobMetrics(meter: Meter) {
  // 既存instrumentは名前・labelとも変更しない。
  const jobsFinished = meter.createCounter("jobs_finished_total");
  const jobsFailed = meter.createCounter("jobs_failed_total");

  const jobDuration = meter.createHistogram("job_duration_seconds", {
    unit: "s",
    advice: {
      explicitBucketBoundaries: JOB_DURATION_BUCKETS_SECONDS,
    },
  });

  function recordJobFinished(input: RecordJobFinishedInput): void {
    const labels = {
      ...baseJobLabels(input.ctx),
      outcome: input.outcome,
    };

    jobsFinished.add(1, labels);
    jobDuration.record(input.durationSeconds, labels);

    if (input.outcome === "failure") {
      jobsFailed.add(1, {
        ...baseJobLabels(input.ctx),
        reason: input.reason ?? "unknown",
      });
    }
  }

  return { recordJobFinished };
}

export const { recordJobFinished } = registerJobMetrics(meter);
```

重要なのは、histogramの属性を`baseJobLabels()`と`outcome`から明示的に作っている点です。`ctx`全体をspreadしないため、`jobName`や`accountId`が紛れ込みません。errorも入力に含めません。

なお、MeterProvider側に同instrument用のViewが設定されている場合、Viewが`advice`より優先される可能性があります。その場合はView側にも同じ境界を設定し、実際のexport結果を統合テストで確認します。

### 呼び出し側

既存のtry/catch内にあった記録を、単一の`finally`へ移します。

```ts
const startedAt = monotonicClock.nowMs();
let completion!: JobCompletion;

try {
  await handler.run(job);
  completion = { outcome: "success" };
} catch (error) {
  completion = {
    outcome: "failure",
    reason: classifyFailure(error),
  };
  throw error;
} finally {
  const finishedAt = monotonicClock.nowMs();
  const durationMs = finishedAt - startedAt;

  recordJobFinished({
    ctx,
    ...completion,
    durationSeconds: durationMs / 1_000,
  });

  logger.info({ durationMs }, "job finished");
}
```

これにより次が保証されます。

- `handler.run(job)`の同期throwも`await`を囲む`catch`で捕捉される。
- success/failureとも、唯一の`finally`から1回だけ記録される。
- clock呼び出しは開始時と終了時の2回だけ。
- histogramとログは同じ`durationMs`を使う。
- failure reasonは従来の`classifyFailure()`をそのまま使う。
- 捕捉した例外は同じオブジェクトを再throwする。

`recordJobFinished`をtry/catchにも残すと二重計測になるため、必ず削除します。

### メトリクス単体テスト

```ts
import type { Meter } from "@opentelemetry/api";
import { registerJobMetrics } from "./job-metrics";

describe("job metrics", () => {
  const jobsFinished = { add: jest.fn() };
  const jobsFailed = { add: jest.fn() };
  const jobDuration = { record: jest.fn() };

  const createCounter = jest
    .fn()
    .mockReturnValueOnce(jobsFinished)
    .mockReturnValueOnce(jobsFailed);
  const createHistogram = jest.fn().mockReturnValue(jobDuration);

  const meter = {
    createCounter,
    createHistogram,
  } as unknown as Meter;

  const { recordJobFinished } = registerJobMetrics(meter);

  const ctx = {
    queue: "critical",
    region: "ap-northeast-1",
    jobName: "send-campaign",
    accountId: "account-123",
  } as const;

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("指定された秒単位とbucketでduration histogramを登録する", () => {
    expect(createHistogram).toHaveBeenCalledWith("job_duration_seconds", {
      unit: "s",
      advice: {
        explicitBucketBoundaries: [0.1, 0.5, 1, 5, 15, 60],
      },
    });
  });

  it("成功した1 jobについてcounterとdurationを1回ずつ記録する", () => {
    recordJobFinished({
      ctx,
      outcome: "success",
      durationSeconds: 1.25,
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

  it("失敗した1 jobについてfailure counterとdurationを1回ずつ記録する", () => {
    recordJobFinished({
      ctx,
      outcome: "failure",
      reason: "timeout",
      durationSeconds: 0.25,
    });

    expect(jobsFinished.add).toHaveBeenCalledTimes(1);
    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: "critical",
      region: "ap-northeast-1",
      reason: "timeout",
    });
    expect(jobDuration.record).toHaveBeenCalledWith(0.25, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "failure",
    });
  });

  it("failure reason省略時は既存どおりunknownを記録する", () => {
    recordJobFinished({
      ctx,
      outcome: "failure",
      durationSeconds: 0.25,
    });

    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: "critical",
      region: "ap-northeast-1",
      reason: "unknown",
    });
  });
});
```

### 実行境界のテスト

特に同期throw、再throw、clockの呼び出し回数を固定します。

```ts
it("handlerが同期throwしてもfailureを1回記録し同じ例外を再throwする", async () => {
  const error = new Error("handler failed");
  const handler = {
    run: jest.fn(() => {
      throw error;
    }),
  };
  const monotonicClock = {
    nowMs: jest.fn().mockReturnValueOnce(1_000).mockReturnValueOnce(2_500),
  };
  const recordJobFinished = jest.fn();
  const logger = { info: jest.fn() };

  const execution = executeJob({
    handler,
    job,
    ctx,
    monotonicClock,
    recordJobFinished,
    classifyFailure: () => "dependency",
    logger,
  });

  await expect(execution).rejects.toBe(error);

  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
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

成功ケースでも同様に、`recordJobFinished`が1回、clockが2回、`durationSeconds`とログの`durationMs`が同じ差分から生成されることを検証します。

作業領域がread-onlyだったため、`referytale`が要求する対応表と`.agent/CONTINUITY.md`は保存できませんでした。その制約下で、名称を増やさず「完了結果」「同じ開始・終了値から得る時間」「一箇所からの記録」を対応させて設計しています。
