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

## Candidate B

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

## Candidate C

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

## Candidate D

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

## Candidate E

最小で一貫する案は、成功・失敗の記録を `finally` の1経路へ集約し、同じ `durationMs` を histogram と既存ログで共有する形です。

## 変更契約

変更する挙動:

- `job_duration_seconds` histogramを追加する。
- 完了した各jobについて、成功・失敗とも1回だけ秒単位で記録する。
- histogramのlabelは `queue`、`region`、`outcome` のみ。

変更しない挙動:

- `jobs_finished_total`、`jobs_failed_total` の名前とlabel。
- `FailureReason` と `unknown` fallback。
- `classifyFailure(error)` による分類。
- 例外の再throw。
- monotonic clockによる計測と既存ログ。

共通処理:

- 終了時刻の取得。
- duration算出。
- finished counter、histogram、ログの記録。

差分処理:

- 成功時は `outcome = "success"`。
- 失敗時だけ `classifyFailure` を実行する。

## 型・登録・記録処理

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
type FailureReason = "timeout" | "dependency" | "invalid_input" | "unknown";
type JobOutcome = "success" | "failure";

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
  durationSeconds: number;
  reason?: FailureReason;
}) {
  const finishedLabels = {
    ...baseJobLabels(input.ctx),
    outcome: input.outcome,
  };

  jobsFinished.add(1, finishedLabels);
  jobDuration.record(input.durationSeconds, finishedLabels);

  if (input.outcome === "failure") {
    jobsFailed.add(1, {
      ...baseJobLabels(input.ctx),
      reason: input.reason ?? "unknown",
    });
  }
}
```

`finishedLabels` をcounterとhistogramで共有するため、両者のlabel規則がずれません。`jobName`、`accountId`、error由来データが流入する経路もありません。

利用中のOpenTelemetryバージョンがinstrumentの `advice.explicitBucketBoundaries` に対応していない場合は、既存の `MeterProvider` のViewで同じ境界を登録します。境界値はinstrument側とView側の両方には定義せず、プロジェクトが採用している一方だけを正本にします。

## 呼び出し側

```ts
const startedAt = monotonicClock.nowMs();

let outcome: JobOutcome = "failure";
let reason: FailureReason | undefined;

try {
  await handler.run(job);
  outcome = "success";
} catch (error) {
  reason = classifyFailure(error);
  throw error;
} finally {
  const durationMs = monotonicClock.nowMs() - startedAt;

  recordJobFinished({
    ctx,
    outcome,
    reason,
    durationSeconds: durationMs / 1_000,
  });

  logger.info({ durationMs }, "job finished");
}
```

重要な点は次のとおりです。

- `recordJobFinished` は `finally` の1か所だけなので二重計測されない。
- `nowMs()` は開始と終了の2回だけ。
- histogramとログが同じ `durationMs` を使う。
- `outcome` をfailureで初期化するため、`handler.run(job)` の同期throwもfailureになる。
- `await` の同期throwとPromise rejectionはいずれも同じ `catch` を通る。
- `throw error` の後でも `finally` が実行され、その後同じ例外が呼び出し元へ伝播する。

## 最小テスト

metrics層ではlabel、値、既存counterを直接検証します。

```ts
describe("recordJobFinished", () => {
  const ctx: JobContext = {
    queue: "critical",
    region: "ap-northeast-1",
    jobName: "send-report",
    accountId: "account-123",
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("成功をcounterとhistogramへ1回記録する", () => {
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

  it("失敗をcounterとhistogramへ1回記録し、reasonを維持する", () => {
    recordJobFinished({
      ctx,
      outcome: "failure",
      reason: "timeout",
      durationSeconds: 0.75,
    });

    expect(jobsFinished.add).toHaveBeenCalledWith(1, {
      queue: "critical",
      region: "ap-northeast-1",
      outcome: "failure",
    });

    expect(jobDuration.record).toHaveBeenCalledTimes(1);
    expect(jobDuration.record).toHaveBeenCalledWith(0.75, {
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

  it("reason省略時は既存どおりunknownを記録する", () => {
    recordJobFinished({
      ctx,
      outcome: "failure",
      durationSeconds: 0.2,
    });

    expect(jobsFailed.add).toHaveBeenCalledWith(1, {
      queue: "critical",
      region: "ap-northeast-1",
      reason: "unknown",
    });
  });
});
```

実行層では、成功と同期throwの境界だけを検証します。

```ts
it("同じmonotonic測定値から成功durationを1回記録する", async () => {
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
    reason: undefined,
    durationSeconds: 1.5,
  });
  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 1_500 },
    "job finished",
  );
});

it("handlerの同期throwをfailureとして1回記録し、同じ例外を再throwする", async () => {
  const error = new Error("handler failed");

  monotonicClock.nowMs
    .mockReturnValueOnce(4_000)
    .mockReturnValueOnce(4_500);
  handler.run.mockImplementation(() => {
    throw error;
  });
  classifyFailure.mockReturnValue("dependency");

  await expect(executeJob(job, ctx)).rejects.toBe(error);

  expect(classifyFailure).toHaveBeenCalledTimes(1);
  expect(classifyFailure).toHaveBeenCalledWith(error);
  expect(monotonicClock.nowMs).toHaveBeenCalledTimes(2);
  expect(recordJobFinished).toHaveBeenCalledTimes(1);
  expect(recordJobFinished).toHaveBeenCalledWith({
    ctx,
    outcome: "failure",
    reason: "dependency",
    durationSeconds: 0.5,
  });
  expect(logger.info).toHaveBeenCalledWith(
    { durationMs: 500 },
    "job finished",
  );
});
```

登録テストまたはSDKのmetric readerを使った統合テストでは、名前が `job_duration_seconds`、unitが `s`、境界が `[0.1, 0.5, 1, 5, 15, 60]` であることを1ケースだけ確認すれば十分です。

作業ディレクトリには実装やテスト構成が存在しなかったため、上記テストは未実行です。導入後の完了条件は、成功・同期throwの各テスト、metrics単体テスト、型チェック、lint、既存テストがすべて成功することです。

## Candidate F

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
