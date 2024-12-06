/*
TimeZone: https://stackoverflow.com/questions/15141762/how-to-initialize-a-javascript-date-to-a-particular-time-zone
TimeZone: https://stackoverflow.com/questions/10087819/convert-date-to-another-timezone-in-javascript
rounding info: https://stackoverflow.com/questions/15762768/javascript-math-round-to-two-decimal-places
*/

function time_update() {
  now = new Date(new Date().toLocaleString('en', {timeZone: 'America/New_York'}))
  a = now.toString().split(' ');
  time_str = a[0] + ' ' + a[1] + ' ' + a[2] + ' ' + a[3] + ' ' + a[4] + ' US/Eastern'
  //console.log(time_str)
  $('[id="time"]').html(time_str);
}

function time_init(symbol_list)
{
  setInterval(time_update, 1000);
}
