const consecanaAtrUrl = 'https://www.consecana.com.br/';

const ignoredOpenTagRegExp = '(?:<(?:font|strong|b|i)[^>]*>)';
const ignoredCloseTagRegExp = '(?:<[/](?:font|strong|b|i)>)';

const atrRegExp = new RegExp(`\
  <tr>
    <td[^>]*>
      ${ignoredOpenTagRegExp}*
        (?<month>jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*
        [/]
        (?<year>2[0-9])
      ${ignoredCloseTagRegExp}*
    <[/]td>
    <td[^>]*>
      ${ignoredOpenTagRegExp}*
        (?<monthlyAtr>[0-9,.]+)
      ${ignoredCloseTagRegExp}*
    <[/]td>
    <td[^>]*>
      ${ignoredOpenTagRegExp}*
        (?<accumulatedAtr>[0-9,.]+)
      ${ignoredCloseTagRegExp}*
    <[/]td>
  <[/]tr>`.split('\n').map(line => line.trim() + '\\s*').join(''),
  'mig');

// all in lower case!
const monthIndexes = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'].reduce(
  (o, month, index) => {
    o[month] = index;
    return o;
  },
  {},
);

async function getConsecanaATRs() {
  const res = await fetch(consecanaAtrUrl);
  if (!res.ok) {
    throw new Error(`${consecanaAtrUrl}: ${res.status} - ${res.statusText}`);
  }
  const html = await res.text();
  const atrs = [];
  for (const match of html.matchAll(atrRegExp)) {
    const {
      month: monthStr,
      year: year2DigitStr,
      monthlyAtr: monthlyAtrStr,
      accumulatedAtr: accumulatedAtrStr,
    } = match.groups;
    const month = monthStr.toLowerCase();
    const monthIndex = monthIndexes[month];
    if (!monthIndex) {
      console.warn(`Ignored invalid month: ${month} not in ${Object.keys(monthIndexes)}`);
      continue;
    }

    const year2Digit = parseInt(year2DigitStr, 10);
    if (isNaN(year2Digit)) {
      console.warn(`Ignored invalid year: ${year2DigitStr}: NaN`);
    }
    const date = new Date(year2Digit + 2000, monthIndex);

    const monthlyAtr = parseFloat(monthlyAtrStr.replace(',', '.'));
    if (isNaN(monthlyAtr)) {
      console.warn(`Ignored invalid monthly ATR: ${monthlyAtrStr}: NaN`);
    }

    const accumulatedAtr = parseFloat(accumulatedAtrStr.replace(',', '.'));
    if (isNaN(accumulatedAtr)) {
      console.warn(`Ignored invalid monthly ATR: ${accumulatedAtrStr}: NaN`);
    }

    atrs.push({ date, monthlyAtr, accumulatedAtr });
  }
  if (!atrs.length) {
    throw new Error(`${consecanaAtrUrl}: could not find any ATRs (html changed?)`);
  }
  atrs.sort(({ date: a }, { date: b }) => {
    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
  });
  return atrs;
}

async function getLastConsecanaATR() {
  const atrs = await getConsecanaATRs();
  return atrs.pop();
}

if (require.main === module) {
    getLastConsecanaATR().then(
      ({ date, monthlyAtr, accumulatedAtr }) => console.log(`${date.toISOString().split('-', 2).join('-')}\t${monthlyAtr}\t${accumulatedAtr}`),
      error => {
        console.error('Error:', error);
        process.exit(1);
      },
    );
}
