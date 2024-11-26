
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

function header_update(symb, info)
{
  th = document.getElementById(symb + "_th");
  remove_all_color(th);
  if(info.currentPrice > info.previousClose) {
    th.classList.add('symb_up');
  } else {
    th.classList.add('symb_down');
  }
}

function update_move_color(e, pct)
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

function move_update(symb, info)
{
  td = document.getElementById(symb + "_move");
  remove_all_color(td);
  move = (info.currentPrice - info.previousClose) / info.previousClose;
  move_pct = (move*100.0).toFixed(2);
  update_move_color(td, move_pct);
  if(move_pct > 0) {
    move_str = '+' + move_pct + '%';
  } else {
    move_str = move_pct + '%';
  }
  td.innerHTML = move_str;
}

function mcap_update(symb, info)
{
  td = document.getElementById(symb + "_mcap");
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

function cell_update(symb, info, datatag)
{
  td = document.getElementById(symb + '_' + datatag);
  if(!td) { return; }
  if(datatag == 'pbRatio') {
    if(typeof(info.bookValue) == "number") {
      data = info.currentPrice / info.bookValue;
    }
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
  }
  if(!data) { return; }
  td.innerHTML = data.toFixed(2);
}

function update_market_data()
{
  $.getJSON( "market_data/market.json", function(data) {
    for (let key in data) {
      //console.log(key, data[key]);
      header_update(key, data[key]);
      move_update(key, data[key]);
      mcap_update(key, data[key]);
      cell_update(key, data[key], 'pbRatio')
      cell_update(key, data[key], 'forwardPE')
      cell_update(key, data[key], 'currentPrice')
      cell_update(key, data[key], 'previousClose')
      cell_update(key, data[key], 'trailingPegRatio')
      cell_update(key, data[key], 'priceToSalesTrailing12Months')
    }
  });
}

function market_data_init(market_data_fetch_interval)
{
  update_market_data(); //Do it once first
  setInterval(update_market_data, market_data_fetch_interval);
}
