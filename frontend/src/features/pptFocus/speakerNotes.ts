/*
 * PPT 演讲者备注（speaker notes）清洗工具。
 *
 * 后端从 PowerPoint 导出的 speaker_notes 末尾有时附带「页码标记」
 * （如 "5"、"第 5 页"、"Page 5"、"5/20"、"Page 5/20"），这是
 * PowerPoint 自动生成、用于打印的水印行，不属于演讲者真正写的内容。
 * 在 PPT 专注页提词器里需要把它过滤掉，避免干扰演讲者阅读。
 */

/**
 * 去除备注末尾的页码行，保留前面的真实备注内容。
 * @param notes 原始 speaker_notes 字符串
 * @param currentPage 当前页码（1-based）
 * @param totalPages 总页数；≤0 表示未知
 * @return 清洗后的备注文本（已 trim）
 */
export function sanitizeSpeakerNotes(
  notes: string,
  currentPage: number,
  totalPages: number,
): string {
  if (!notes.trim()) return '';
  const lines = notes.replace(/\r/g, '').split('\n');
  while (lines.length && !lines[lines.length - 1]?.trim()) {
    lines.pop();
  }
  const lastLine = lines[lines.length - 1]?.trim() ?? '';
  const normalizedLastLine = lastLine.toLowerCase().replace(/\s+/g, '');
  const markers = new Set(
    [
      String(currentPage),
      `第${currentPage}页`,
      `page${currentPage}`,
      totalPages > 0 ? `${currentPage}/${totalPages}` : '',
      totalPages > 0 ? `page${currentPage}/${totalPages}` : '',
    ]
      .filter(Boolean)
      .map((item) => item.toLowerCase().replace(/\s+/g, '')),
  );
  if (markers.has(normalizedLastLine)) {
    lines.pop();
  }
  return lines.join('\n').trim();
}
