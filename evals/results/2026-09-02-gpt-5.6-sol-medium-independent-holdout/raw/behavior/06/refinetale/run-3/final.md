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
