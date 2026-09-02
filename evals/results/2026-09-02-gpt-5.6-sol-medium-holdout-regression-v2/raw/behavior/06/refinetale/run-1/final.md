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
