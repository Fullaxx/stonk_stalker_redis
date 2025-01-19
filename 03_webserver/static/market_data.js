
function remove_all_color(e)
{
  e.classList.remove('symb_up');
  e.classList.remove('symb_down');
  e.classList.remove('pos_eight');
  e.classList.remove('pos_seven');
  e.classList.remove('pos_six');
  e.classList.remove('pos_five');
  e.classList.remove('pos_four');
  e.classList.remove('pos_three');
  e.classList.remove('pos_two');
  e.classList.remove('pos_one');
  e.classList.remove('pos_small');
  e.classList.remove('neg_small');
  e.classList.remove('neg_one');
  e.classList.remove('neg_two');
  e.classList.remove('neg_three');
  e.classList.remove('neg_four');
  e.classList.remove('neg_five');
  e.classList.remove('neg_six');
  e.classList.remove('neg_seven');
  e.classList.remove('neg_eight');
}

function header_update(info)
{
  symb = info.symbol
  th = document.getElementById(symb + '_th');
  if(!th) { return; }
  remove_all_color(th);
  if(info.currentPrice > info.previousClose) {
    th.classList.add('symb_up');
  } else {
    th.classList.add('symb_down');
  }
}

function update_color(e, pct)
{
       if(pct >=  8) { e.classList.add('pos_eight'); }
  else if(pct <= -8) { e.classList.add('neg_eight'); }
  else if(pct >=  7) { e.classList.add('pos_seven'); }
  else if(pct <= -7) { e.classList.add('neg_seven'); }
  else if(pct >=  6) { e.classList.add('pos_six'); }
  else if(pct <= -6) { e.classList.add('neg_six'); }
  else if(pct >=  5) { e.classList.add('pos_five'); }
  else if(pct <= -5) { e.classList.add('neg_five'); }
  else if(pct >=  4) { e.classList.add('pos_four'); }
  else if(pct <= -4) { e.classList.add('neg_four'); }
  else if(pct >=  3) { e.classList.add('pos_three'); }
  else if(pct <= -3) { e.classList.add('neg_three'); }
  else if(pct >=  2) { e.classList.add('pos_two'); }
  else if(pct <= -2) { e.classList.add('neg_two'); }
  else if(pct >=  1) { e.classList.add('pos_one'); }
  else if(pct <= -1) { e.classList.add('neg_one'); }
  else if(pct  >  0) { e.classList.add('pos_small'); }
  else if(pct  <  0) { e.classList.add('neg_small'); }
}

function move_update(info)
{
  symb = info.symbol
  td = document.getElementById(symb + '_move');
  if(!td) { return; }
  remove_all_color(td);
  if(typeof(info.previousClose) != 'number') { return; }
  if(typeof(info.currentPrice) != 'number') { return; }
  move = (info.currentPrice - info.previousClose) / info.previousClose;
  move_pct = (move*100.0).toFixed(2);
  update_color(td, move_pct);
  if(move_pct > 0) {
    move_str = '+' + move_pct + '%';
  } else {
    move_str = move_pct + '%';
  }
  td.innerHTML = move_str;
}

function ytd_update(info)
{
  symb = info.symbol
  td = document.getElementById(symb + '_ytd');
  if(!td) { return; }
  remove_all_color(td);
  if(typeof(info.lastYearClose) != 'number') { return; }
  if(typeof(info.currentPrice) != 'number') { return; }
  ytd = (info.currentPrice - info.lastYearClose) / info.lastYearClose;
  ytd_pct = (ytd*100.0).toFixed(2);
  update_color(td, ytd_pct);
  if(ytd_pct > 0) {
    move_str = '+' + ytd_pct + '%';
  } else {
    move_str = ytd_pct + '%';
  }
  td.innerHTML = move_str;
}

function mcap_update(info)
{
  symb = info.symbol
  td = document.getElementById(symb + '_mcap');
  if(!td) { return; }
  mcap = info.marketCap;
  if(mcap >= 1e12) {
    value = mcap/1e12;
    units = 'T';
  } else if(mcap >= 1e9) {
    value = mcap/1e9;
    units = 'B';
  } else {
    value = mcap/1e6;
    units = 'M';
  }
  td.innerHTML = value.toFixed(1) + units;
}

function cell_update(info, datatag)
{
  symb = info.symbol
  td = document.getElementById(symb + '_' + datatag);
  if(!td) { return; }

  // Default value
  data = '';

  if(datatag == 'pbRatio') {
    if(typeof(info.bookValue) != 'number') { return; }
    if(typeof(info.currentPrice) != 'number') { return; }
    data = info.currentPrice / info.bookValue;
  } else if(datatag == 'trailingPegRatio') {
    data = info.trailingPegRatio;
  } else if(datatag == 'priceToSalesTrailing12Months') {
    data = info.priceToSalesTrailing12Months;
  } else if(datatag == 'forwardPE') {
    data = info.forwardPE;
  } else if(datatag == 'previousClose') {
    data = info.previousClose;
  } else if(datatag == 'currentPrice') {
    data = info.currentPrice;
  } else if(datatag == 'dtr') {
    data = info.dtr;
  }

  if(typeof(data) == 'number') {
    td.innerHTML = data.toFixed(2);
  } else if(typeof(data) == 'string') {
    td.innerHTML = data;
  }
}

function update_symbol(obj)
{
  header_update(obj);
  move_update(obj);
  ytd_update(obj);
  mcap_update(obj);
  cell_update(obj, 'dtr');
  cell_update(obj, 'pbRatio');
  cell_update(obj, 'forwardPE');
  cell_update(obj, 'currentPrice');
  cell_update(obj, 'previousClose');
  cell_update(obj, 'trailingPegRatio');
  cell_update(obj, 'priceToSalesTrailing12Months');
}

function update_market_data_via_getJSON()
{
  //console.log('update_market_data_via_getJSON()')

  $.getJSON( 'market_data/marketdb.json', function(data) {
    //console.log(data)
    for (let key in data) {
      //console.log(key, data[key]);
      symbobj = data[key];
      update_symbol(symbobj);
    }
  }).fail(function(xhr, status, error) {
    console.log('getJSON() FAILED! ' + status + ' ' + error + ' ' + xhr.status + ' ' + xhr.statusText);
  });
}

function update_market_data_via_object()
{
  $.get('market_data/marketdb.json', function(data) {
    const jsonobj = JSON.parse(data);
    for (let key in jsonobj) {
      symbobj = jsonobj[key];
      update_symbol(symbobj);
    }
  }).fail(function(xhr, status, error) {
    console.log('get() FAILED! ' + status + ' ' + error + ' ' + xhr.status + ' ' + xhr.statusText);
  });
}

function update_market_data_via_list()
{
  $.get('market_data/marketlist.json', function(data) {
    const jsonarray = JSON.parse(data);
    for (i in jsonarray) {
      symbobj = jsonarray[i];
      update_symbol(symbobj);
    }
  }).fail(function(xhr, status, error) {
    console.log('get() FAILED! ' + status + ' ' + error + ' ' + xhr.status + ' ' + xhr.statusText);
  });
}

function market_data_init(market_data_fetch_interval)
{
  update_market_data_via_list(); //Do it once first
  setInterval(update_market_data_via_list, market_data_fetch_interval);
}
