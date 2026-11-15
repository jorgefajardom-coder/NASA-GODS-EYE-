import { describe, expect, it } from 'vitest';
import { DEFAULT_ROVER_CAMERA, ROVER_CAMERAS, cameraFovDeg, focusText, mastcamFocalFromId, mastcamFovDeg, mastcamNearFocusM, roverCameraOf } from '../src/lib/roverCameras';

describe('real Perseverance cameras', () => {
  it('keeps the published fields of view, focus ranges and baselines (Maki et al. 2020; Bell et al. 2021)', () => {
    expect([ROVER_CAMERAS.navcam.hFovDeg, ROVER_CAMERAS.navcam.vFovDeg]).toEqual([96, 73]);
    expect([ROVER_CAMERAS.hazcam_front.hFovDeg, ROVER_CAMERAS.hazcam_front.vFovDeg]).toEqual([136, 102]);
    expect([ROVER_CAMERAS.mastcamz.hFovDeg, ROVER_CAMERAS.mastcamz.vFovDeg]).toEqual([25.6, 19.2]);
    expect(ROVER_CAMERAS.navcam.focusM.nearM).toBe(1.5);
    expect(ROVER_CAMERAS.hazcam_rear.focusM.nearM).toBe(0.8);
    expect(ROVER_CAMERAS.watson.focusM.nearM).toBe(0.018);
    expect(ROVER_CAMERAS.navcam.baselineM).toBe(0.424);
    expect(ROVER_CAMERAS.mastcamz.baselineM).toBe(0.244);
    expect(ROVER_CAMERAS.hazcam_front.baselineM).toBe(0.25);
    expect(ROVER_CAMERAS.hazcam_rear.baselineM).toBe(0.934);
  });

  it('zooms only Mastcam-Z, from 19.2 deg at 26 mm to about 4.6 deg at 110 mm', () => {
    expect(mastcamFovDeg(26)).toBeCloseTo(19.2, 1);
    expect(mastcamFovDeg(110)).toBeCloseTo(4.6, 1);
    expect(mastcamFovDeg(500)).toBeCloseTo(4.6, 1); // clamped to the zoom's end
    expect(cameraFovDeg(ROVER_CAMERAS.navcam, 110)).toBe(73); // fixed lens
    expect(mastcamNearFocusM(34)).toBe(0.5);
    expect(mastcamNearFocusM(100)).toBe(1);
  });

  it('reads the Mastcam-Z focal length from the image ID', () => {
    expect(mastcamFocalFromId('ZL0_2024_0846622583_145EBY_N0930000ZCAM10058_1100LMJ')).toBe(110);
    expect(mastcamFocalFromId('ZR0_0001_0667022672_000EBY_N0010052AUT_04096_0340LMJ')).toBe(34);
    expect(mastcamFocalFromId('NLG_2024_0846619972_104ECM_N0930000NCAM00520_00_2I4J')).toBeNull();
  });

  it('views through the Navcam by default', () => {
    expect(DEFAULT_ROVER_CAMERA.id).toBe('navcam');
  });

  it('names the camera and the eye of the stereo pair that took a photo, for Perseverance only', () => {
    expect(roverCameraOf('NAVCAM_LEFT')).toMatchObject({ camera: { id: 'navcam' }, side: 'left' });
    expect(roverCameraOf('MCZ_RIGHT')).toMatchObject({ camera: { id: 'mastcamz' }, side: 'right' });
    expect(roverCameraOf('FRONT_HAZCAM_RIGHT_A')).toMatchObject({ camera: { id: 'hazcam_front' }, side: 'right' });
    expect(roverCameraOf('REAR_HAZCAM_LEFT')).toMatchObject({ camera: { id: 'hazcam_rear' }, side: 'left' });
    expect(roverCameraOf('SHERLOC_WATSON')?.camera.id).toBe('watson');
    expect(roverCameraOf('SUPERCAM_RMI')).toBeNull();
    expect(roverCameraOf('FHAZ_LEFT_B', 'Curiosity')).toBeNull();
  });

  it('puts every camera on a node of the model, and fixes the Hazcams to the body', () => {
    expect(ROVER_CAMERAS.navcam.mount).toBe('mast');
    expect(ROVER_CAMERAS.hazcam_front.mount).toBe('body');
    expect(ROVER_CAMERAS.hazcam_rear.boresight?.azDeg).toBe(180);
    expect(ROVER_CAMERAS.watson.mount).toBe('arm');
    expect(focusText(1.5, null)).toBe('1.5 m – ∞');
    expect(focusText(0.018, null)).toBe('1.8 cm – ∞');
  });
});
