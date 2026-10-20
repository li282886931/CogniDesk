const statusLabels: Record<string, string> = {
  ROBOT_HANDLING: "机器人接待",
  HUMAN_HANDLING: "人工处理中",
  TICKET_CREATED: "工单处理中",
  RESOLVED: "已解决",
  CLOSED: "已关闭",
  OPEN: "待处理",
  PROCESSING: "处理中",
  SOLVED: "已解决"
};

export function formatStatus(status: string): string {
  return statusLabels[status] ?? status;
}
