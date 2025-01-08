/*
TimeZone: https://stackoverflow.com/questions/15141762/how-to-initialize-a-javascript-date-to-a-particular-time-zone
TimeZone: https://stackoverflow.com/questions/10087819/convert-date-to-another-timezone-in-javascript
rounding info: https://stackoverflow.com/questions/15762768/javascript-math-round-to-two-decimal-places
*/

function market_clock_update() {
  now = new Date(new Date().toLocaleString('en', {timeZone: 'America/New_York'}))
  a = now.toString().split(' ');
  time_str = 'Current Time: ' + a[0] + ' ' + a[1] + ' ' + a[2] + ' ' + a[3] + ' ' + a[4] + ' US/Eastern'
  //console.log(time_str)
  $('[id="marketclock"]').html(time_str);
}

function market_clock_init()
{
  setInterval(market_clock_update, 1000);
}

/*
// Just in case we have more trouble with inline javascript
$(document).ready(function(){ market_clock_init(); });
*/

function update_market_status()
{
  $.get('market_data/market_status.json', function(data) {
    const market_status = JSON.parse(data);
    //console.log(jsonobj)
    is_open = market_status['is_open']
    if (is_open) {
      status_str='Market: Open (Closes @ ' + market_status['next_close'] + ')'
    } else {
      status_str='Market: Closed (Opens @ ' + market_status['next_open'] + ')'
    }
    $('[id="marketstatus"]').html(status_str);
  }).fail(function(xhr, status, error) {
    console.log('get() FAILED! ' + status + ' ' + error + ' ' + xhr.status + ' ' + xhr.statusText);
  });
}

function market_status_init()
{
  var market_status_html = $('[id="marketstatus"]').html();
  if (market_status_html == 'MARKETSTATUSINIT') {
    update_market_status(); //Do it once first
    setInterval(update_market_status, 10000);
  }
}
