import { describe, expect, it } from 'vitest';
import { DEFAULT_ROVER_CAMERA, MOUNT_EYE, ROVER_CAMERAS, ROVER_FOV_RANGE_DEG, mountOf, roverCameraOf } from '../src/lib/roverCameras';

describe('real Perseverance cameras', () => {
  it('keeps the published fields of view (WashU PDS page; Bell et al. 2021)', () => {
    expect([ROVER_CAMERAS.navcam.hFovDeg, ROVER_CAMERAS.navcam.vFovDeg]).toEqual([96, 73]);
    expect([ROVER_CAMERAS.hazcam.hFovDeg, ROVER_CAMERAS.hazcam.vFovDeg]).toEqual([136, 102]);
    expect([ROVER_CAMERAS.mastcamz.hFovDeg, ROVER_CAMERAS.mastcamz.vFovDeg]).toEqual([25.6, 19.2]);
    expect(ROVER_CAMERAS.mastcamz.minVFovDeg).toBe(4.6); // 110 mm end of the zoom
  });

  it('views through the Navcam by default and limits the zoom to what the cameras give', () => {
    expect(DEFAULT_ROVER_CAMERA.id).toBe('navcam');
    expect(ROVER_FOV_RANGE_DEG).toEqual({ min: 4.6, max: 102 });
  });

  it('names the camera of a photo from the feed instrument, for Perseverance only', () => {
    expect(roverCameraOf('NAVCAM_LEFT')?.id).toBe('navcam');
    expect(roverCameraOf('MCZ_RIGHT')?.id).toBe('mastcamz');
    expect(roverCameraOf('FRONT_HAZCAM_LEFT_A')?.id).toBe('hazcam');
    expect(roverCameraOf('REAR_HAZCAM_RIGHT')?.id).toBe('hazcam');
    expect(roverCameraOf('SUPERCAM_RMI')).toBeNull(); // no field of view checked for it
    expect(roverCameraOf('FHAZ_LEFT_B', 'Curiosity')).toBeNull();
  });

  it('puts mast cameras on the mast and Hazcams at the front or the rear of the body', () => {
    expect(mountOf(ROVER_CAMERAS.navcam, 'NAVCAM_LEFT', null)).toBe('mast');
    expect(mountOf(ROVER_CAMERAS.hazcam, 'FRONT_HAZCAM_LEFT_A', null)).toBe('front');
    expect(mountOf(ROVER_CAMERAS.hazcam, 'REAR_HAZCAM_RIGHT', null)).toBe('rear');
    expect(mountOf(ROVER_CAMERAS.hazcam, 'HAZCAM', [-0.2, 0.5, 0.8])).toBe('rear');
    expect(MOUNT_EYE.mast.upM).toBeGreaterThan(MOUNT_EYE.front.upM);
    expect(MOUNT_EYE.rear.forwardM).toBeLessThan(0);
  });
});
