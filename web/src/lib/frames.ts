export interface EnuPoint { x: number; y: number; z: number }

/** ROS map ENU metres -> Three.js x east, y up, z south. */
export function enuToThree({ x, y, z }: EnuPoint): [number, number, number] {
  if (![x, y, z].every(Number.isFinite)) throw new Error("ENU coordinates must be finite metres");
  return [x, z, y === 0 ? 0 : -y];
}
