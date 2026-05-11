/*
 * 设计系统出口：业务侧仅从此处导入组件，避免散落的相对路径。
 */
export { default as FButton } from './FButton.vue';
export { default as FCard } from './FCard.vue';
export { default as FIcon } from './FIcon.vue';
export { default as FInput } from './FInput.vue';
export { default as FTextarea } from './FTextarea.vue';
export { default as FField } from './FField.vue';
export { default as FSwitch } from './FSwitch.vue';
export { default as FSlider } from './FSlider.vue';
export { default as FSegmented } from './FSegmented.vue';
export { default as FTag } from './FTag.vue';
export { default as FSpinner } from './FSpinner.vue';
export { default as FSkeleton } from './FSkeleton.vue';
export { default as FProgress } from './FProgress.vue';
export { default as FDialog } from './FDialog.vue';
export { default as FDialogHost } from './FDialogHost.vue';
export { default as FDrawer } from './FDrawer.vue';
export { default as FMessageBar } from './FMessageBar.vue';
export { default as FToastHost } from './FToastHost.vue';
export { default as FEmpty } from './FEmpty.vue';
export { default as FTabs } from './FTabs.vue';
export { default as FCombobox } from './FCombobox.vue';
export { default as FMenu } from './FMenu.vue';
export { default as FTooltip } from './FTooltip.vue';
export { default as FDivider } from './FDivider.vue';

export type { FluentIconName } from './icons';
export {
    type ButtonAppearance,
    type ButtonSize,
    type TagTone,
    type MessageTone,
    type FSegmentedOption,
    type FTabsItem,
    type FComboboxOption,
    type FMenuItem,
    type FMenuGroup,
} from './types';
