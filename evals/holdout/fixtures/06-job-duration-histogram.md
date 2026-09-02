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
