You are grading six anonymized answers to an independent holdout evaluation. Return only the requested structured result.

# 06: Add a job-duration histogram

## Purpose

既存の完了計測点とbounded labelを保ち、二重計測や高cardinalityを増やさずmetricを追加できるか確認する。

## Input

ジョブ実行の既存メトリクスに、完了したジョブの所要時間histogramを追加します。既存の計測点とlabel規則を維持し、二重計測や高カーディナリティを起こさない変更案を、型・登録・記録処理・テストまで示してください。

既存metrics:

```ts
const jobsFinished = meter.createCounter("jobs_finished_total");
const jobsFailed = meter.createCounter("jobs_failed_total");

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
  outcome: "success" | "failure";
  reason?: FailureReason;
}) {
  jobsFinished.add(1, { ...baseJobLabels(input.ctx), outcome: input.outcome });
  if (input.outcome === "failure") {
    jobsFailed.add(1, {
      ...baseJobLabels(input.ctx),
      reason: input.reason ?? "unknown",
    });
  }
}
```

呼び出し側:

```ts
const startedAt = monotonicClock.nowMs();
try {
  await handler.run(job);
  recordJobFinished({ ctx, outcome: "success" });
} catch (error) {
  recordJobFinished({ ctx, outcome: "failure", reason: classifyFailure(error) });
  throw error;
} finally {
  logger.info({ durationMs: monotonicClock.nowMs() - startedAt }, "job finished");
}
```

新要件:

- histogram名は`job_duration_seconds`、unitはseconds、bucketは`[0.1, 0.5, 1, 5, 15, 60]`。
- labelは`queue`、`region`、`outcome`だけ。`jobName`、`accountId`、error messageは禁止。
- 成功/失敗とも完了した1 jobにつき1 observation。
- 既存counterの名前、label、failure reason分類は変えない。
- durationは既存monotonic clockの1組の測定値から算出し、別timerやwall clockを追加しない。
- `handler.run`が同期的にthrowしてもfailureとして1回計測し、例外は従来どおり再throwする。

## Pass conditions

- **S1 Measurement point:** 既存の完了経路にdurationを一度だけ渡してcounterとhistogramを記録し、別wrapper/timerや成功・失敗別の重複instrument callを作らない。
- **S2 Duration:** 既存monotonic `startedAt`と完了時刻の差をmsで一度求め、secondsへ変換して指定bucket/unitのhistogramに記録する。
- **S3 Label boundary:** `baseJobLabels`を共用し、boundedな`outcome`だけを足す。禁止labelや任意string mapを使わない。
- **S4 Existing contracts:** counter名・label・failure reason・rethrowを維持し、成功、async failure、sync throwを過不足なく記録する。
- **S5 Verification:** 成功/失敗/sync throwの回数、ms-to-seconds、指定labelのみ、bucket/unit、counter回帰、禁止label不在を確認する。

## Critical failure conditions

- `jobName`、`accountId`、error messageのいずれかをmetric labelへ使う。
- 1 jobを成功/失敗経路と`finally`の両方で二重観測し得る。
- wall clockを追加して既存monotonic clockと混在させる。

## Scoring

S1〜S5を各0〜2点で採点する。2点はinstrument登録、計測点への値の受け渡し、unit、label、例外経路、testが一貫して具体的、1点は一部曖昧、0点は二重計測・契約変更・高cardinality・計算誤り・重要な欠落がある。8〜10点かつ0点なしをPass、6〜7点または0点を含む8点以上をBorderline、5点以下をFailとする。critical failureを最優先し、helper名やコード構造との一致ではなく観測可能な挙動で判定する。


## Judge instructions

Score each candidate independently using only its final answer and this fixture.
Do not guess its generation condition. The workspace intentionally contained no source files and
was read-only, so judge the proposed data flow, types, boundaries, failure behavior, and observable
test plan. Do not fail a candidate merely because it could not edit or execute code.

Score S1 through S5 from 0 to 2 exactly as defined by the fixture. `total` must equal their sum.
If any critical failure condition is met, set `critical_failure` to true and `outcome` to
`critical_failure`. Otherwise use: pass = total 8-10 with every S at least 1; borderline = total
6-7, or total 8-10 with any S equal to 0; fail = total 0-5. Evidence must name concrete satisfied
and missing behavior. Do not reward headings, verbosity, or terminology by itself.


## Candidate A

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

## Candidate B

変更案は、完了状態を1つの値に集約し、`finally`内の単一経路で終了時刻取得・既存counter・histogram・ログを記録する形です。これにより成功／失敗でduration計算を複製せず、完了1件につき1 observationを構造的に保証できます。

## 変更契約

変更する挙動:

- `job_duration_seconds`へ成功・失敗とも1回記録する。
- durationは既存の`startedAt`と、`finally`で取得する終了値の差だけから算出する。
- histogram属性は`queue`、`region`、`outcome`のみ。

変更しない挙動:

- `jobs_finished_total`の名前と属性。
- `jobs_failed_total`の名前と属性。
- `classifyFailure`による分類と、未指定時の`unknown`。
- handler例外の再throw。
- 既存のdurationログ。
- wall clockや追加timerは導入しない。

共通処理:

- 成功・失敗とも同じ`finally`でdurationと完了metricsを記録する。

差分処理:

- 成功は`outcome: "success"`。
- 失敗だけ`classifyFailure`を実行し、`reason`を保持して再throwする。

## 型とmetrics登録

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

type JobContext = {
  queue: QueueName;
  region: Region;
  jobName: string;
  accountId: string;
};

export type JobCompletion =
  | {
      outcome: "success";
    }
  | {
      outcome: "failure";
      reason?: FailureReason;
    };
```

bucket定数は登録時にしか使わないため、設定用の汎用抽象化や外部設定にはしません。

`advice.explicitBucketBoundaries`を利用できるのは対応するOpenTelemetry API/SDKの場合です。インストール版が対応していなければ、同じ境界を`MeterProvider`の対象instrument限定Viewに設定します。両方には設定しません。OpenTelemetry JSではinstrument側の`advice`例と、SDK Viewによる明示的bucket設定の両方が示されています。[OpenTelemetry JS metrics](https://github.com/open-telemetry/opentelemetry-js/blob/main/doc/metrics.md)

## 記録処理

clockはmsを返し、既存ログもmsを使うため、`recordJobFinished`には`durationMs`を渡します。secondsへの変換はhistogramのunitを所有するmetrics側に一度だけ置きます。

```ts
function baseJobLabels(ctx: JobContext) {
  return { queue: ctx.queue, region: ctx.region } as const;
}

export function recordJobFinished(
  input: {
    ctx: JobContext;
    durationMs: number;
  } & JobCompletion,
) {
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

`completionLabels`はcounterとhistogramで共用しますが、失敗counterには渡しません。そのため属性は次のまま固定されます。

- `jobs_finished_total`: `queue`, `region`, `outcome`
- `jobs_failed_total`: `queue`, `region`, `reason`
- `job_duration_seconds`: `queue`, `region`, `outcome`

`jobName`、`accountId`、例外オブジェクト、error messageが属性経路に入る場所はありません。

## 呼び出し側

```ts
const startedAt = monotonicClock.nowMs();
let completion: JobCompletion = { outcome: "success" };

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

`handler.run(job)`の同期throwも`try`内で発生するため、同じ`catch`でfailureへ変換されます。その後、再throw前に必ず`finally`が実行され、failureを1回記録します。

また、成功側の`recordJobFinished`を`try`内に残さないことが重要です。成功metricsやloggerが例外を投げた場合に、その例外をhandler失敗として`catch`し、failureを重ねて記録する経路を作らないためです。

## 最小テスト

metrics層では属性・変換・既存counterを、ジョブ実行層ではclock回数・単一記録・再throwを検証します。

```ts
describe("recordJobFinished", () => {
  const ctx: JobContext = {
    queue: "critical",
    region: "ap-northeast-1",
    jobName: "send-report",
    accountId: "account-123",
  };

  it("成功counterとdurationを指定属性で記録する", () => {
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
    expect(jobsFailed.add).not.toHaveBeenCalled();
    expect(jobDuration.record).toHaveBeenCalledTimes(1);
    expect(jobDuration.record).toHaveBeenCalledWith(1.5, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "success",
    });
  });

  it("失敗counterのreasonを維持しdurationを1回記録する", () => {
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

  it("reason未指定時は既存どおりunknownを使う", () => {
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

ジョブ実行層には次の3経路が必要です。

```ts
it.each([
  ["非同期reject", () => Promise.reject(jobError)],
  [
    "同期throw",
    () => {
      throw jobError;
    },
  ],
])("%sをfailureとして1回記録し、同じ例外を再throwする", async (_, run) => {
  handler.run.mockImplementation(run);
  monotonicClock.nowMs
    .mockReturnValueOnce(10_000)
    .mockReturnValueOnce(11_500);
  classifyFailure.mockReturnValue("dependency");

  await expect(executeJob()).rejects.toBe(jobError);

  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
  expect(recordJobFinished).toHaveBeenCalledTimes(1);
  expect(recordJobFinished).toHaveBeenCalledWith({
    ctx,
    outcome: "failure",
    reason: "dependency",
    durationMs: 1_500,
  });
  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 1_500 },
    "job finished",
  );
});
```

成功経路も同様に、clockが2回、`recordJobFinished`が1回、`outcome: "success"`、同じ`durationMs`がログへ渡ることを確認します。

| 契約 | 検証 | 期待結果 |
|---|---|---|
| histogram名・unit・bucket | 登録テスト | 指定値と完全一致 |
| 成功1 jobにつき1 observation | 成功実行テスト | `record`が1回 |
| 非同期失敗1 jobにつき1 observation | rejectテスト | failureが1回、再throw |
| 同期throwもfailure | 同期throwテスト | failureが1回、同一例外を再throw |
| 禁止labelなし | `record`引数の完全一致 | 3属性のみ |
| 既存counter維持 | metrics単体テスト | 名前・属性・reasonが従来どおり |
| 同じclock測定値を利用 | clock呼び出し回数と引数検証 | 開始・終了の計2回、metricsとログが同じ差分 |

ワークスペースには実装ファイルやテスト環境が存在しなかったため、上記テストは未実行です。実リポジトリでは最初にOpenTelemetryの導入版と既存`MeterProvider`設定を確認し、`advice`かViewの一方へ確定する必要があります。

## Candidate C

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

## Candidate D

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

## Candidate E

提案は、`recordJobFinished` を唯一のメトリクス記録点として維持し、呼び出し側では既存の monotonic clock から得た `durationMs` を1回だけ確定させる形です。

## 変更契約

変更する挙動:

- 完了した各ジョブについて `job_duration_seconds` を1回記録する。
- 値は `durationMs / 1000`。
- label は `queue`、`region`、`outcome`だけ。
- 成功、非同期失敗、同期 throw のすべてを同じ完了経路へ合流させる。

変更しない挙動:

- `jobs_finished_total`、`jobs_failed_total` の名前とlabel。
- `FailureReason` と `classifyFailure`。
- failure reason の `"unknown"` fallback。
- 元の例外の再throw。
- ログの `durationMs`。
- clock は開始時と完了時の計2回だけ呼ぶ。

## 型・登録・記録処理

`durationMs` を受け取るのは、呼び出し側と clock の単位を一致させ、秒変換の正本を histogram 側に限定するためです。

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
  outcome: "success" | "failure";
  reason?: FailureReason;
  durationMs: number;
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

  jobDuration.record(input.durationMs / 1000, completionLabels);
}
```

`completionLabels` を counter と histogram で共有するため、`jobName`、`accountId`、error message が histogram へ混入する別経路を作りません。failure counter には従来どおり `outcome` を渡さず、`reason` を維持します。

OpenTelemetry JSでは `unit: "s"` と `advice.explicitBucketBoundaries` が対応する指定です。[公式実装例](https://github.com/open-telemetry/opentelemetry-js/blob/main/experimental/packages/opentelemetry-instrumentation-http/src/http.ts)でも同じ形式が使われています。

ただし、matching View が存在すると instrument の bucket advice より View が優先されます。[OpenTelemetry Metrics仕様](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md)に従い、既存の `MeterProvider` に `job_duration_seconds` 対象の View がないことを確認します。既にある場合は、bucket の正本をその View に置き、instrument 側との二重定義は避けます。

## 呼び出し側

成功・失敗を別々の場所で記録すると二重計測防止をコード構造だけで保証できません。failure reason だけを保持し、`finally` の単一経路で時間・メトリクス・ログを確定します。

```ts
const startedAt = monotonicClock.nowMs();
let failureReason: FailureReason | undefined;

try {
  await handler.run(job);
} catch (error) {
  failureReason = classifyFailure(error);
  throw error;
} finally {
  const durationMs = monotonicClock.nowMs() - startedAt;

  recordJobFinished({
    ctx,
    outcome: failureReason === undefined ? "success" : "failure",
    reason: failureReason,
    durationMs,
  });

  logger.info({ durationMs }, "job finished");
}
```

これにより:

- `nowMs()` は開始と終了の2回だけ。
- histogram とログが同じ `durationMs` を使用。
- `handler.run(job)` の同期 throw も `try` 内で評価されるため `catch` される。
- `recordJobFinished` は `finally` の1か所からだけ呼ばれる。
- `throw error` により元の例外を再throwする。

別timer、wall clock、`didFail` のような重複booleanは不要です。

## 必要なテスト

### メトリクス責務

```ts
it("registers the duration histogram with seconds and explicit buckets", () => {
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

it("records one successful completion with only completion labels", () => {
  recordJobFinished({
    ctx: {
      queue: "critical",
      region: "ap-northeast-1",
      jobName: "send-email",
      accountId: "account-123",
    },
    outcome: "success",
    durationMs: 1500,
  });

  expect(jobsFinished.add).toHaveBeenCalledTimes(1);
  expect(jobsFinished.add).toHaveBeenCalledWith(1, {
    queue: "critical",
    region: "ap-northeast-1",
    outcome: "success",
  });
  expect(jobsFailed.add).not.toHaveBeenCalled();
  expect(jobDuration.record).toHaveBeenCalledTimes(1);
  expect(jobDuration.record).toHaveBeenCalledWith(1.5, {
    queue: "critical",
    region: "ap-northeast-1",
    outcome: "success",
  });
});

it("preserves failure counter labels and records one failure duration", () => {
  recordJobFinished({
    ctx,
    outcome: "failure",
    reason: "timeout",
    durationMs: 500,
  });

  expect(jobsFinished.add).toHaveBeenCalledWith(1, {
    queue: ctx.queue,
    region: ctx.region,
    outcome: "failure",
  });
  expect(jobsFailed.add).toHaveBeenCalledWith(1, {
    queue: ctx.queue,
    region: ctx.region,
    reason: "timeout",
  });
  expect(jobDuration.record).toHaveBeenCalledTimes(1);
  expect(jobDuration.record).toHaveBeenCalledWith(0.5, {
    queue: ctx.queue,
    region: ctx.region,
    outcome: "failure",
  });
});
```

完全一致でlabelを検証するため、禁止された `jobName`、`accountId`、error message の不在も同時に保証できます。

### 実行経路

最低限、次の3ケースを呼び出し側のテストに置きます。

| 経路 | clock | 完了記録 | 例外 |
|---|---:|---:|---|
| resolve | 2回 | successで1回 | なし |
| Promise reject | 2回 | failureで1回 | 同一例外を再throw |
| 同期 throw | 2回 | failureで1回 | 同一例外を再throw |

代表的な同期 throw の検証:

```ts
it("records a synchronously thrown job once and rethrows the same error", async () => {
  const error = new Error("boom");

  monotonicClock.nowMs
    .mockReturnValueOnce(1_000)
    .mockReturnValueOnce(2_250);

  handler.run.mockImplementation(() => {
    throw error;
  });
  classifyFailure.mockReturnValue("dependency");

  await expect(runJob(job, ctx)).rejects.toBe(error);

  expect(classifyFailure).toHaveBeenCalledTimes(1);
  expect(classifyFailure).toHaveBeenCalledWith(error);
  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
  expect(recordJobFinished).toHaveBeenCalledTimes(1);
  expect(recordJobFinished).toHaveBeenCalledWith({
    ctx,
    outcome: "failure",
    reason: "dependency",
    durationMs: 1_250,
  });
  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 1_250 },
    "job finished",
  );
});
```

実プロジェクトファイルが作業ディレクトリに存在せず、環境も読み取り専用だったため、実装・テスト実行・`.agent/CONTINUITY.md` 作成は未実施です。実装時の完了条件は、上記テストに加え、実際の SDK で export された histogram 境界が指定値と一致すること、ビルド・lint・型チェックが成功することです。

## Candidate F

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
