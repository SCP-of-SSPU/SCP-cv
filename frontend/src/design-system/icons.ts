/*
 * Fluent SVG 图标静态注册表。
 *
 * 设计取舍：
 * 1. `@fluentui/svg-icons` 提供 2 万+ 图标，禁止整体 import 以免开发期 / 产物体积失控。
 * 2. 业务用图标全部在此文件以 `import …?raw` 显式登记；新增图标时同步追加一行即可。
 * 3. 提供 `name → svg 文本` 的 Map，业务侧通过 `<FIcon name="home_24_regular" />` 调用。
 *
 * 命名沿用 Fluent 原始 `name_size_variant`（小写下划线），便于与官方文档/Figma 对照。
 */

// ── 导入：仅按需登记，不要批量 glob 全量包 ─────────────────────────
import home_24_regular from '@fluentui/svg-icons/icons/home_24_regular.svg?raw';
import home_24_filled from '@fluentui/svg-icons/icons/home_24_filled.svg?raw';
import tv_24_regular from '@fluentui/svg-icons/icons/tv_24_regular.svg?raw';
import tv_24_filled from '@fluentui/svg-icons/icons/tv_24_filled.svg?raw';
import desktop_24_regular from '@fluentui/svg-icons/icons/desktop_24_regular.svg?raw';
import desktop_mac_24_regular from '@fluentui/svg-icons/icons/desktop_mac_24_regular.svg?raw';
import library_24_regular from '@fluentui/svg-icons/icons/library_24_regular.svg?raw';
import library_24_filled from '@fluentui/svg-icons/icons/library_24_filled.svg?raw';
import layer_24_regular from '@fluentui/svg-icons/icons/layer_24_regular.svg?raw';
import layer_24_filled from '@fluentui/svg-icons/icons/layer_24_filled.svg?raw';
import settings_24_regular from '@fluentui/svg-icons/icons/settings_24_regular.svg?raw';
import settings_24_filled from '@fluentui/svg-icons/icons/settings_24_filled.svg?raw';
import alert_24_regular from '@fluentui/svg-icons/icons/alert_24_regular.svg?raw';
import alert_urgent_24_regular from '@fluentui/svg-icons/icons/alert_urgent_24_regular.svg?raw';
import info_24_regular from '@fluentui/svg-icons/icons/info_24_regular.svg?raw';
import navigation_24_regular from '@fluentui/svg-icons/icons/navigation_24_regular.svg?raw';
import dismiss_24_regular from '@fluentui/svg-icons/icons/dismiss_24_regular.svg?raw';
import dismiss_20_regular from '@fluentui/svg-icons/icons/dismiss_20_regular.svg?raw';
import dismiss_16_regular from '@fluentui/svg-icons/icons/dismiss_16_regular.svg?raw';
import add_24_regular from '@fluentui/svg-icons/icons/add_24_regular.svg?raw';
import add_20_regular from '@fluentui/svg-icons/icons/add_20_regular.svg?raw';
import arrow_clockwise_24_regular from '@fluentui/svg-icons/icons/arrow_clockwise_24_regular.svg?raw';
import arrow_clockwise_20_regular from '@fluentui/svg-icons/icons/arrow_clockwise_20_regular.svg?raw';
import arrow_left_24_regular from '@fluentui/svg-icons/icons/arrow_left_24_regular.svg?raw';
import arrow_right_24_regular from '@fluentui/svg-icons/icons/arrow_right_24_regular.svg?raw';
import chevron_down_20_regular from '@fluentui/svg-icons/icons/chevron_down_20_regular.svg?raw';
import chevron_up_20_regular from '@fluentui/svg-icons/icons/chevron_up_20_regular.svg?raw';
import chevron_left_20_regular from '@fluentui/svg-icons/icons/chevron_left_20_regular.svg?raw';
import chevron_right_20_regular from '@fluentui/svg-icons/icons/chevron_right_20_regular.svg?raw';
import chevron_left_24_regular from '@fluentui/svg-icons/icons/chevron_left_24_regular.svg?raw';
import chevron_right_24_regular from '@fluentui/svg-icons/icons/chevron_right_24_regular.svg?raw';
import play_24_regular from '@fluentui/svg-icons/icons/play_24_regular.svg?raw';
import play_24_filled from '@fluentui/svg-icons/icons/play_24_filled.svg?raw';
import pause_24_regular from '@fluentui/svg-icons/icons/pause_24_regular.svg?raw';
import pause_24_filled from '@fluentui/svg-icons/icons/pause_24_filled.svg?raw';
import stop_24_regular from '@fluentui/svg-icons/icons/stop_24_regular.svg?raw';
import previous_24_regular from '@fluentui/svg-icons/icons/previous_24_regular.svg?raw';
import next_24_regular from '@fluentui/svg-icons/icons/next_24_regular.svg?raw';
import arrow_repeat_all_24_regular from '@fluentui/svg-icons/icons/arrow_repeat_all_24_regular.svg?raw';
import arrow_repeat_all_off_24_regular from '@fluentui/svg-icons/icons/arrow_repeat_all_off_24_regular.svg?raw';
import speaker_2_24_regular from '@fluentui/svg-icons/icons/speaker_2_24_regular.svg?raw';
import speaker_2_20_regular from '@fluentui/svg-icons/icons/speaker_2_20_regular.svg?raw';
import speaker_mute_24_regular from '@fluentui/svg-icons/icons/speaker_mute_24_regular.svg?raw';
import speaker_mute_20_regular from '@fluentui/svg-icons/icons/speaker_mute_20_regular.svg?raw';
import speaker_off_24_regular from '@fluentui/svg-icons/icons/speaker_off_24_regular.svg?raw';
import document_24_regular from '@fluentui/svg-icons/icons/document_24_regular.svg?raw';
import video_24_regular from '@fluentui/svg-icons/icons/video_24_regular.svg?raw';
import image_24_regular from '@fluentui/svg-icons/icons/image_24_regular.svg?raw';
import music_note_2_24_regular from '@fluentui/svg-icons/icons/music_note_2_24_regular.svg?raw';
import globe_24_regular from '@fluentui/svg-icons/icons/globe_24_regular.svg?raw';
import live_24_regular from '@fluentui/svg-icons/icons/live_24_regular.svg?raw';
import arrow_upload_24_regular from '@fluentui/svg-icons/icons/arrow_upload_24_regular.svg?raw';
import arrow_download_24_regular from '@fluentui/svg-icons/icons/arrow_download_24_regular.svg?raw';
import delete_24_regular from '@fluentui/svg-icons/icons/delete_24_regular.svg?raw';
import delete_20_regular from '@fluentui/svg-icons/icons/delete_20_regular.svg?raw';
import pin_24_regular from '@fluentui/svg-icons/icons/pin_24_regular.svg?raw';
import pin_24_filled from '@fluentui/svg-icons/icons/pin_24_filled.svg?raw';
import pin_off_24_regular from '@fluentui/svg-icons/icons/pin_off_24_regular.svg?raw';
import edit_24_regular from '@fluentui/svg-icons/icons/edit_24_regular.svg?raw';
import edit_20_regular from '@fluentui/svg-icons/icons/edit_20_regular.svg?raw';
import open_24_regular from '@fluentui/svg-icons/icons/open_24_regular.svg?raw';
import arrow_swap_24_regular from '@fluentui/svg-icons/icons/arrow_swap_24_regular.svg?raw';
import power_24_regular from '@fluentui/svg-icons/icons/power_24_regular.svg?raw';
import plug_disconnected_24_regular from '@fluentui/svg-icons/icons/plug_disconnected_24_regular.svg?raw';
import arrow_reset_24_regular from '@fluentui/svg-icons/icons/arrow_reset_24_regular.svg?raw';
import search_24_regular from '@fluentui/svg-icons/icons/search_24_regular.svg?raw';
import search_20_regular from '@fluentui/svg-icons/icons/search_20_regular.svg?raw';
import filter_24_regular from '@fluentui/svg-icons/icons/filter_24_regular.svg?raw';
import more_horizontal_24_regular from '@fluentui/svg-icons/icons/more_horizontal_24_regular.svg?raw';
import more_horizontal_20_regular from '@fluentui/svg-icons/icons/more_horizontal_20_regular.svg?raw';
import link_24_regular from '@fluentui/svg-icons/icons/link_24_regular.svg?raw';
import checkmark_24_regular from '@fluentui/svg-icons/icons/checkmark_24_regular.svg?raw';
import checkmark_20_regular from '@fluentui/svg-icons/icons/checkmark_20_regular.svg?raw';
import checkmark_circle_24_filled from '@fluentui/svg-icons/icons/checkmark_circle_24_filled.svg?raw';
import error_circle_24_filled from '@fluentui/svg-icons/icons/error_circle_24_filled.svg?raw';
import error_circle_20_filled from '@fluentui/svg-icons/icons/error_circle_20_filled.svg?raw';
import warning_24_filled from '@fluentui/svg-icons/icons/warning_24_filled.svg?raw';
import warning_20_filled from '@fluentui/svg-icons/icons/warning_20_filled.svg?raw';
import arrow_maximize_24_regular from '@fluentui/svg-icons/icons/arrow_maximize_24_regular.svg?raw';
import arrow_minimize_24_regular from '@fluentui/svg-icons/icons/arrow_minimize_24_regular.svg?raw';
import apps_list_24_regular from '@fluentui/svg-icons/icons/apps_list_24_regular.svg?raw';
import spinner_ios_20_regular from '@fluentui/svg-icons/icons/spinner_ios_20_regular.svg?raw';
import eye_24_regular from '@fluentui/svg-icons/icons/eye_24_regular.svg?raw';
import eye_off_24_regular from '@fluentui/svg-icons/icons/eye_off_24_regular.svg?raw';
import star_24_regular from '@fluentui/svg-icons/icons/star_24_regular.svg?raw';
import star_24_filled from '@fluentui/svg-icons/icons/star_24_filled.svg?raw';

const ICONS = {
  home_24_regular,
  home_24_filled,
  tv_24_regular,
  tv_24_filled,
  desktop_24_regular,
  desktop_mac_24_regular,
  library_24_regular,
  library_24_filled,
  layer_24_regular,
  layer_24_filled,
  settings_24_regular,
  settings_24_filled,
  alert_24_regular,
  alert_urgent_24_regular,
  info_24_regular,
  navigation_24_regular,
  dismiss_24_regular,
  dismiss_20_regular,
  dismiss_16_regular,
  add_24_regular,
  add_20_regular,
  arrow_clockwise_24_regular,
  arrow_clockwise_20_regular,
  arrow_left_24_regular,
  arrow_right_24_regular,
  chevron_down_20_regular,
  chevron_up_20_regular,
  chevron_left_20_regular,
  chevron_right_20_regular,
  chevron_left_24_regular,
  chevron_right_24_regular,
  play_24_regular,
  play_24_filled,
  pause_24_regular,
  pause_24_filled,
  stop_24_regular,
  previous_24_regular,
  next_24_regular,
  arrow_repeat_all_24_regular,
  arrow_repeat_all_off_24_regular,
  speaker_2_24_regular,
  speaker_2_20_regular,
  speaker_mute_24_regular,
  speaker_mute_20_regular,
  speaker_off_24_regular,
  document_24_regular,
  video_24_regular,
  image_24_regular,
  music_note_2_24_regular,
  globe_24_regular,
  live_24_regular,
  arrow_upload_24_regular,
  arrow_download_24_regular,
  delete_24_regular,
  delete_20_regular,
  pin_24_regular,
  pin_24_filled,
  pin_off_24_regular,
  edit_24_regular,
  edit_20_regular,
  open_24_regular,
  arrow_swap_24_regular,
  power_24_regular,
  plug_disconnected_24_regular,
  arrow_reset_24_regular,
  search_24_regular,
  search_20_regular,
  filter_24_regular,
  more_horizontal_24_regular,
  more_horizontal_20_regular,
  link_24_regular,
  checkmark_24_regular,
  checkmark_20_regular,
  checkmark_circle_24_filled,
  error_circle_24_filled,
  error_circle_20_filled,
  warning_24_filled,
  warning_20_filled,
  arrow_maximize_24_regular,
  arrow_minimize_24_regular,
  apps_list_24_regular,
  spinner_ios_20_regular,
  eye_24_regular,
  eye_off_24_regular,
  star_24_regular,
  star_24_filled,
} as const;

export type FluentIconName = keyof typeof ICONS;

const FALLBACK_SVG = '<svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"></svg>';

/**
 * 获取指定图标的 SVG 字符串。
 * @param name 已登记的图标名称
 * @return SVG 文本，可直接 `v-html` 注入
 */
export function getIconSvg(name: FluentIconName | string): string {
  return (ICONS as Record<string, string>)[name] ?? FALLBACK_SVG;
}

/** 调试辅助：返回当前已登记的图标数量。 */
export function loadedIconCount(): number {
  return Object.keys(ICONS).length;
}
