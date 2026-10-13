// Mirrors the CSS custom properties in styles.css (dataviz reference palette, dark steps).
// S/I/R validated all-pairs on the dark surface. The contact layer is colored by S/I/R
// (hollow = quarantining); the social layer by informed vs. uninformed (slash = won't
// adhere), so each layer shows only its own process. With misinformation on, the social
// layer adds misinformed (magenta, the reference palette's dark magenta step). It is
// close to the uninformed gray under protan CVD, so misinformed nodes always also carry
// the won't-adhere slash (misinformed = non-adherent) and its chart line has its own dash.
export const COLORS = {
  surface: '#1a1a19',
  page: '#0d0d0d',
  text: '#f0efec',
  text2: '#c3c2b7',
  muted: '#898781',
  grid: '#2c2c2a',
  axis: '#383835',
  S: '#3987e5',
  I: '#d95926',
  R: '#199e70',
  informed: '#c98500',
  uninformed: '#6f7889',
  misinformed: '#d55181',
  quarantine: '#9085e9',
  select: '#f0efec',
};

// Accent per multiplex slot (frames, badges, tabs), kept clear of the state hues above.
// Mirrors --slot-0..2 in styles.css.
export const SLOT_COLORS = ['#e6e4dc', '#e377c2', '#17becf'];
export const SLOT_NAMES = ['A', 'B', 'C'];

export const STATE_COLORS = [COLORS.S, COLORS.I, COLORS.R];
export const STATE_NAMES = ['Susceptible', 'Infected', 'Recovered'];

export function hexToRgb(hex) {
  const h = hex.replace('#', '');
  return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255);
}
