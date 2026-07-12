export type ControlCommandStatus = 'pending' | 'executing' | 'succeeded' | 'failed' | 'cancelled';

export interface ControlCommandState {
  id: number;
  target: 'window:1' | 'window:2' | 'window:3' | 'window:4' | 'background_audio';
  command: string;
  status: ControlCommandStatus;
  error_message: string;
}
