import { describe, it, expect } from 'vitest';
import { TEAM, TIMELINE, PAPER, CONTACT } from '@/lib/about-data';

describe('about data', () => {
  it('team has 3+ members', () => {
    expect(TEAM.length).toBeGreaterThanOrEqual(3);
  });

  it('every team member has name + role + bio + tags', () => {
    TEAM.forEach((m) => {
      expect(m.name).toBeTruthy();
      expect(m.role).toBeTruthy();
      expect(m.bio).toBeTruthy();
      expect(m.tags.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('timeline is ordered by version', () => {
    const versions = TIMELINE.map((t) => t.version);
    expect(versions[0]).toBe('v1.0');
    expect(versions[versions.length - 1]).toMatch(/v5\.0/);
  });

  it('timeline has major milestones', () => {
    const majors = TIMELINE.filter((t) => t.major);
    expect(majors.length).toBeGreaterThanOrEqual(2);
    expect(majors.some((m) => m.version === 'v3.0')).toBe(true);
    expect(majors.some((m) => m.version === 'v4.0')).toBe(true);
  });

  it('paper has all key data', () => {
    expect(PAPER.title).toContain('CoPiano v3');
    expect(PAPER.results.length).toBeGreaterThanOrEqual(4);
    expect(PAPER.code.scripts).toBeGreaterThan(0);
  });

  it('paper results include d=1.34', () => {
    const dResult = PAPER.results.find((r) => r.metric === "Cohen's d");
    expect(dResult?.value).toBe('1.34');
  });

  it('contact info has required fields', () => {
    expect(CONTACT.email).toMatch(/@/);
    expect(CONTACT.github).toMatch(/^https?:\/\//);
    expect(CONTACT.wechat).toBeTruthy();
  });
});
