// Clay configuration page for Tens. Each item's messageKey matches the keys
// declared in package.json and read in src/c/settings.c. Mirrors UserConfig.

// Accent choice (color1/color2 + slot colors). Values match the C enums in
// settings.h (TENS_COLOR_* / TENS_VIS_* / TENS_SLOT_*).
var COLOR_OPTIONS = [
  { label: 'Orange', value: 0 },
  { label: 'Blue', value: 1 },
  { label: 'Gray', value: 2 },
];

var VISIBILITY_OPTIONS = [
  { label: 'Never', value: 0 },
  { label: 'Weekdays', value: 1 },
  { label: 'Weekends', value: 2 },
  { label: 'Always', value: 3 },
];

var SLOT_COLOR_OPTIONS = [
  { label: 'Color 1', value: 0 },
  { label: 'Color 2', value: 1 },
  { label: 'Muted', value: 2 },
];

// One hour-slot's four controls. `defaults` is {start, end, vis, color}.
function slotItems(n, defaults) {
  return [
    { type: 'heading', defaultValue: 'Slot ' + n },
    {
      type: 'input',
      messageKey: 'SLOT' + n + '_START',
      label: 'Start hour (0-23)',
      attributes: { type: 'number', min: 0, max: 23 },
      defaultValue: String(defaults.start),
    },
    {
      type: 'input',
      messageKey: 'SLOT' + n + '_END',
      label: 'End hour (0-23, exclusive)',
      attributes: { type: 'number', min: 0, max: 23 },
      defaultValue: String(defaults.end),
    },
    {
      type: 'select',
      messageKey: 'SLOT' + n + '_VISIBILITY',
      label: 'Show on',
      defaultValue: defaults.vis,
      options: VISIBILITY_OPTIONS,
    },
    {
      type: 'select',
      messageKey: 'SLOT' + n + '_COLOR',
      label: 'Color',
      defaultValue: defaults.color,
      options: SLOT_COLOR_OPTIONS,
    },
  ];
}

module.exports = [
  { type: 'heading', defaultValue: 'Tens' },
  {
    type: 'section',
    items: [
      { type: 'heading', defaultValue: 'Day grid' },
      {
        type: 'toggle',
        messageKey: 'RAINBOW',
        label: 'Rainbow (spectral grid)',
        defaultValue: false,
      },
      {
        type: 'toggle',
        messageKey: 'DARK_MODE',
        label: 'Dark mode (black background)',
        defaultValue: false,
      },
      {
        type: 'toggle',
        messageKey: 'LAYOUT_4X6',
        label: 'Layout 4x6 (3x2 cells, vs 6x4)',
        defaultValue: false,
      },
      {
        type: 'toggle',
        messageKey: 'HOURS_HORIZONTAL',
        label: 'Hours fill horizontally (vs vertically)',
        defaultValue: true,
      },
      {
        type: 'toggle',
        messageKey: 'BARS_MISSING_STYLE',
        label: 'Bars: fill missing parts (vs outline)',
        defaultValue: true,
      },
      {
        type: 'toggle',
        messageKey: 'BOX_MISSING_STYLE',
        label: 'Current 10-min block: fill missing part (vs outline)',
        defaultValue: true,
      },
      {
        type: 'toggle',
        messageKey: 'MINUTE_NUMBER',
        label: 'Show minute number (0-9) in current 10-min block',
        defaultValue: true,
      },
    ],
  },
  {
    type: 'section',
    items: [
      { type: 'heading', defaultValue: 'Colors' },
      {
        type: 'select',
        messageKey: 'COLOR1',
        label: 'Color 1 (left top bar)',
        defaultValue: 0,
        options: COLOR_OPTIONS,
      },
      {
        type: 'select',
        messageKey: 'COLOR2',
        label: 'Color 2 (right top bar)',
        defaultValue: 1,
        options: COLOR_OPTIONS,
      },
    ],
  },
  {
    type: 'section',
    items: [
      { type: 'heading', defaultValue: 'Bars' },
      {
        type: 'select',
        messageKey: 'BAR_SET',
        label: 'Bars show',
        defaultValue: 4,
        options: [
          { label: 'Month / Year / Life', value: 0 },
          { label: 'Week / Month / Year', value: 1 },
          { label: 'Slot 1 / Week / Month', value: 2 },
          { label: 'Slot 1 / Slot 2 / Week', value: 3 },
          { label: 'Day / Month / Life', value: 4 },
        ],
      },
      {
        type: 'toggle',
        messageKey: 'BAR_NUMBERS',
        label: 'Show day & month numbers (Day / Month / Life only)',
        defaultValue: true,
      },
      {
        type: 'select',
        messageKey: 'START_OF_WEEK',
        label: 'Week starts on',
        defaultValue: 0,
        options: [
          { label: 'Monday', value: 0 },
          { label: 'Sunday', value: 1 },
        ],
      },
    ],
  },
  {
    type: 'section',
    items: [{ type: 'heading', defaultValue: 'Hour slots' }]
      .concat(slotItems(1, { start: 9, end: 17, vis: 0, color: 0 }))
      .concat(slotItems(2, { start: 23, end: 7, vis: 0, color: 1 }))
      .concat(slotItems(3, { start: 0, end: 0, vis: 0, color: 2 }))
      .concat(slotItems(4, { start: 0, end: 0, vis: 0, color: 2 })),
  },
  {
    type: 'section',
    items: [
      { type: 'heading', defaultValue: 'You' },
      {
        type: 'input',
        messageKey: 'BIRTH_YEAR',
        label: 'Birth year',
        attributes: { type: 'number', min: 1900, max: 2100 },
        defaultValue: '1990',
      },
      {
        type: 'input',
        messageKey: 'BIRTH_MONTH',
        label: 'Birth month (1-12)',
        attributes: { type: 'number', min: 1, max: 12 },
        defaultValue: '4',
      },
      {
        type: 'input',
        messageKey: 'BIRTH_DAY',
        label: 'Birth day (1-31)',
        attributes: { type: 'number', min: 1, max: 31 },
        defaultValue: '12',
      },
      {
        type: 'input',
        messageKey: 'LIFE_SPAN_YEARS',
        label: 'Life span (years)',
        attributes: { type: 'number', min: 1, max: 150 },
        defaultValue: '80',
      },
    ],
  },
  { type: 'submit', defaultValue: 'Save' },
];
