/*
 * Material Symbols 图标映射表（DESIGN.md §9 IC1：全应用仅用 Material Symbols，
 * 不混用图标库）。
 *
 * 设计取舍：
 * 1. 业务侧仍以既有名 token（`home_24_regular` 等）调用 `<FIcon name="…" />`，
 *    本表把它翻译为对应的 Material Symbols 连字（ligature）名；
 *    这样彻底移除 `@fluentui/svg-icons`，又无需改动 40+ 调用点。
 * 2. 字体由 `material-symbols/rounded.css` 提供（在 main.ts 引入），
 *    渲染为 `<span class="material-symbols-rounded">play_arrow</span>`，
 *    与 DESIGN.md §14.4 范例一致。
 * 3. `FluentIconName` 仍为联合类型，保持全仓库类型约束不变。
 */

const SYMBOL_MAP = {
  add_24_regular: 'add',
  add_20_regular: 'add',
  alert_24_regular: 'notifications',
  alert_urgent_24_regular: 'notification_important',
  apps_list_24_regular: 'apps',
  arrow_clockwise_24_regular: 'refresh',
  arrow_clockwise_20_regular: 'refresh',
  arrow_download_24_regular: 'download',
  arrow_left_24_regular: 'arrow_back',
  arrow_right_24_regular: 'arrow_forward',
  arrow_maximize_24_regular: 'open_in_full',
  arrow_minimize_24_regular: 'close_fullscreen',
  arrow_repeat_all_24_regular: 'repeat',
  arrow_repeat_all_off_24_regular: 'sync_disabled',
  arrow_reset_24_regular: 'restart_alt',
  arrow_swap_24_regular: 'swap_horiz',
  arrow_upload_24_regular: 'upload',
  checkmark_16_filled: 'check',
  checkmark_20_regular: 'check',
  checkmark_24_regular: 'check',
  checkmark_circle_24_filled: 'check_circle',
  chevron_down_20_regular: 'expand_more',
  chevron_up_20_regular: 'expand_less',
  chevron_left_20_regular: 'chevron_left',
  chevron_left_24_regular: 'chevron_left',
  chevron_right_20_regular: 'chevron_right',
  chevron_right_24_regular: 'chevron_right',
  dark_theme_24_regular: 'brightness_medium',
  delete_24_regular: 'delete',
  delete_20_regular: 'delete',
  desktop_24_regular: 'desktop_windows',
  desktop_mac_24_regular: 'desktop_mac',
  dismiss_24_regular: 'close',
  dismiss_20_regular: 'close',
  dismiss_16_regular: 'close',
  document_24_regular: 'description',
  edit_24_regular: 'edit',
  edit_20_regular: 'edit',
  error_circle_24_filled: 'error',
  error_circle_20_filled: 'error',
  eye_24_regular: 'visibility',
  eye_off_24_regular: 'visibility_off',
  filter_24_regular: 'filter_list',
  full_screen_maximize_24_regular: 'fullscreen',
  full_screen_minimize_24_regular: 'fullscreen_exit',
  globe_24_regular: 'public',
  home_24_regular: 'home',
  home_24_filled: 'home',
  image_24_regular: 'image',
  info_24_regular: 'info',
  layer_24_regular: 'layers',
  layer_24_filled: 'layers',
  library_24_regular: 'perm_media',
  library_24_filled: 'perm_media',
  link_24_regular: 'link',
  live_24_regular: 'live_tv',
  more_horizontal_24_regular: 'more_horiz',
  more_horizontal_20_regular: 'more_horiz',
  music_note_2_24_regular: 'music_note',
  navigation_24_regular: 'menu',
  next_24_regular: 'skip_next',
  previous_24_regular: 'skip_previous',
  open_24_regular: 'open_in_new',
  pause_24_regular: 'pause',
  pause_24_filled: 'pause',
  pin_24_regular: 'push_pin',
  pin_24_filled: 'push_pin',
  pin_off_24_regular: 'keep_off',
  play_24_regular: 'play_arrow',
  play_24_filled: 'play_arrow',
  plug_disconnected_24_regular: 'power_off',
  power_24_regular: 'power_settings_new',
  radio_button_24_regular: 'radio_button_unchecked',
  radio_button_24_filled: 'radio_button_checked',
  search_24_regular: 'search',
  search_20_regular: 'search',
  settings_24_regular: 'settings',
  settings_24_filled: 'settings',
  speaker_2_24_regular: 'volume_up',
  speaker_2_20_regular: 'volume_up',
  speaker_mute_24_regular: 'volume_off',
  speaker_mute_20_regular: 'volume_off',
  speaker_off_24_regular: 'volume_off',
  spinner_ios_20_regular: 'progress_activity',
  star_24_regular: 'star',
  star_24_filled: 'star',
  stop_24_regular: 'stop',
  subtract_16_filled: 'remove',
  tv_24_regular: 'tv',
  tv_24_filled: 'tv',
  video_24_regular: 'movie',
  warning_24_filled: 'warning',
  warning_20_filled: 'warning',
  weather_moon_24_regular: 'dark_mode',
  weather_sunny_24_regular: 'light_mode',
} as const;

export type FluentIconName = keyof typeof SYMBOL_MAP;

/** 未登记名兜底：用通用占位连字，避免布局抖动。 */
const FALLBACK_SYMBOL = 'circle';

/**
 * 把既有图标名解析为 Material Symbols 连字名。
 * @param name 业务侧使用的图标名 token（或已是 Material Symbols 连字）
 * @return Material Symbols 连字字符串，可直接作为字体图标文本
 */
export function resolveSymbol(name: FluentIconName | string): string {
  return (SYMBOL_MAP as Record<string, string>)[name] ?? name ?? FALLBACK_SYMBOL;
}

/** 调试辅助：返回当前已登记的图标映射数量。 */
export function loadedIconCount(): number {
  return Object.keys(SYMBOL_MAP).length;
}
