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
