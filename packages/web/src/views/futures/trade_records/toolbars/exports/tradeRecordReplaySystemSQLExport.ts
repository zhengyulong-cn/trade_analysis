/**
 * 导入教程：
 * 1.连接tradereplay.db文件，找到accounts、imported_trades表，前者维护账户，后者维护交易记录
 * 2.查看imported_trades最后一条记录的id，然后修改STARTID，避免重复
 * 3.在前端页面筛选正确时间，然后点击导出sql功能
 */
import type { TradeRecord } from "@/api/modules";
import { saveAs } from "file-saver"

import dayjs from "dayjs";
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
dayjs.extend(utc);
dayjs.extend(timezone);

interface TradeReplaySystemRecordAPI {
  id?: number;                         // INTEGER
  account_id?: number;                 // INTEGER
  ticket_id?: string;                  // TEXT
  symbol?: string;                     // TEXT
  type?: string;                       // TEXT
  open_time?: number;                  // INTEGER (时间戳)
  close_time?: number;                 // INTEGER
  open_price?: number;                 // REAL
  close_price?: number;                // REAL
  volume?: number;                     // REAL
  stop_loss?: number;                  // REAL
  take_profit?: number;                // REAL
  commission?: number;                 // REAL
  swap?: number;                       // REAL
  taxes?: number;                      // REAL
  profit?: number;                     // REAL
  hedge_to?: string;                   // TEXT
  hedge_from?: string;                 // TEXT
  notes?: string;                      // TEXT
  tags_json?: string;                  // TEXT (JSON字符串)
  reflection?: string;                 // TEXT
  source_file?: string;                // TEXT
  imported_at?: number;                // INTEGER (时间戳)
  mae?: number;                        // REAL (Maximum Adverse Excursion)
  mfe?: number;                        // REAL (Maximum Favorable Excursion)
  user_id?: string;                    // TEXT
  remote_id?: string;                  // TEXT
  version?: number;                    // INTEGER
  synced_at?: number;                  // INTEGER (时间戳)
  dirty?: number;                      // INTEGER (布尔值，0/1)
  strategy_id?: number;                // INTEGER
  ai_review_id?: number;               // INTEGER
  checklist_completed_json?: string;   // TEXT (JSON字符串)
  screenshot?: string;                 // TEXT
  strategy_name?: string;              // TEXT
  entry_reason?: string;               // TEXT
}

const getTimestamp = () => {
  const date = new Date()
  const pad = (value: number) => String(value).padStart(2, "0")
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(
    date.getMinutes(),
  )}${pad(date.getSeconds())}`
}

const formatSymbol = (oldSymbol: string): string => {
  // 匹配字母前缀和数字后缀
  const match = oldSymbol.match(/^([a-zA-Z]+)(\d+)$/);
  if (!match) {
    // 如果格式不匹配，原样返回或根据需求处理
    return oldSymbol;
  }
  let letters = match[1];
  let numbers = match[2];
  if(!letters || !numbers) {
    return ''
  }
  // 字母部分转大写
  let upperLetters = letters.toUpperCase();
  // 数字部分：若为三位数，则在前面补 '2' 变为四位数
  if (numbers.length === 3) {
    numbers = '2' + numbers;
  }
  return upperLetters + numbers;
};

const formatDate = (oldDate: string): number => {
  const timestampMs = dayjs.tz(oldDate, 'Asia/Shanghai').valueOf()
  return Math.floor(timestampMs / 1000)
}

export const formatExportRecord = (
  record: TradeRecord,
  newRecordId: number
) => {
  const { data_json } = record
  const open_time = formatDate(data_json["open_time"] as string)
  const close_time = formatDate(data_json["close_time"] as string)
  const ticket_id = `${open_time}-${close_time}`
  const formatObj: TradeReplaySystemRecordAPI = {
    id: newRecordId,
    account_id: Number(data_json["account_id"]),
    ticket_id: ticket_id,
    symbol: formatSymbol(data_json["contract"] as string),
    type: data_json["open_direction"] == "short" ? "sell" : "buy",
    open_time: open_time,
    open_price: data_json["open_price"] as number,
    close_time: close_time,
    close_price: data_json["close_price"] as number,
    volume: data_json["lots"] as number,
    commission: data_json["fee"] as number,
    swap: 0,
    taxes: 0,
    profit: data_json["operate_pnl"] as number,
    tags_json: '[]',
    imported_at: dayjs().valueOf(),
    user_id: 'local',
  }
  console.log(formatObj)
  const sql = `INSERT INTO "main"."imported_trades" (
	"id",
	"account_id",
	"ticket_id",
	"symbol",
	"type",
	"open_time",
	"close_time",
	"open_price",
	"close_price",
	"volume",
	"stop_loss",
	"take_profit",
	"commission",
	"swap",
	"taxes",
	"profit",
	"hedge_to",
	"hedge_from",
	"notes",
	"tags_json",
	"reflection",
	"source_file",
	"imported_at",
	"mae",
	"mfe",
	"user_id",
	"remote_id",
	"version",
	"synced_at",
	"dirty",
	"strategy_id",
	"ai_review_id",
	"checklist_completed_json",
	"screenshot",
	"strategy_name",
	"entry_reason" 
)
VALUES
	(
		${formatObj.id},
		${formatObj.account_id},
		'${formatObj.ticket_id}',
		'${formatObj.symbol}',
		'${formatObj.type}',
		${formatObj.open_time},
		${formatObj.close_time},
		${formatObj.open_price},
		${formatObj.close_price},
		${formatObj.volume},
		NULL,
		NULL,
		${formatObj.commission},
		0.0,
		0.0,
		${formatObj.profit},
		NULL,
		NULL,
		'',
		'[]',
		'',
		NULL,
		${formatObj.imported_at},
		NULL,
		NULL,
		'${formatObj.user_id}',
		NULL,
		1,
		NULL,
		1,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
    NULL 
	);
  `
  return sql
}

const STARTID = 526

export const tradeRecordReplaySystemSQLExport = (
    records: TradeRecord[],
) => {
  const rows = records.map((record, i) => formatExportRecord(record, STARTID + i))
  const content = rows.join('\n');
  // 生成 Blob，指定 MIME 类型为纯文本或 application/sql
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  // 触发下载
  saveAs(blob, `交易记录_${getTimestamp()}.sql`);
}