import { assetUrl } from '../data/replayAdapter';

/** Portrait shown beside an agent's name in the details panel. */
export interface Portrait {
  url: string;
  alt: string;
}

/**
 * Agent portraits. human_1's is an AI-generated image (ChatGPT, supplied by the team) with an
 * "AI-generated" watermark burned into the file, so it stays visible in every capture
 * (docs/AI_USAGE.md). It is an illustration, not a photo of a crew member.
 */
export const PORTRAITS: Record<string, Portrait> = {
  human_1: { url: assetUrl('assets/portraits/human_1.webp'), alt: 'Astronaut human_1 portrait (AI-generated illustration)' },
};
