function toggleHidden(e)
{
  if (e.hidden) {
    e.removeAttribute('hidden');
  } else {
    e.setAttribute('hidden', true);
  }
}

function toggleHiddenID(id)
{
  var e = document.getElementById(id)
  toggleHidden(e)
}

function toggleHiddenClass(className)
{
  var elements = document.getElementsByClassName(className)
  for(var i = 0; i < elements.length; i++) {
    toggleHidden(elements[i])
  }
}

/*
function toggleGridHidden() { toggleHiddenID('ercalgrid'); }
function toggleListHidden() { toggleHiddenID('ercallist'); }
*/

function ercal_dropdown_selected()
{
  var d = document.getElementById('ercal_dropedown');
  var i = d.selectedIndex
  var selectedValue = d.options[i].value

  //console.log(i, d.options[i], selectedValue)

  if (selectedValue == 'none') {
    document.getElementById('ercalgrid').setAttribute('hidden', true);
    document.getElementById('ercallist').setAttribute('hidden', true);
  }

  if (selectedValue == 'grid') {
    document.getElementById('ercalgrid').removeAttribute('hidden');
    document.getElementById('ercallist').setAttribute('hidden', true);
  }

  if (selectedValue == 'list') {
    document.getElementById('ercalgrid').setAttribute('hidden', true);
    document.getElementById('ercallist').removeAttribute('hidden');
  }
}

function html_config_init()
{
  document.getElementById('ercal_dropedown').addEventListener('click', ercal_dropdown_selected);
}

function update_ytd_rows()     { toggleHiddenClass('ytd_row');     }
function update_bb_rows()      { toggleHiddenClass('bb_row');      }
function update_macd_rows()    { toggleHiddenClass('macd_row');    }
function update_support_rows() { toggleHiddenClass('support_row'); }
function update_sma200_rows()  { toggleHiddenClass('sma200_row');  }
function update_mcap_rows()    { toggleHiddenClass('mcap_row');    }
function update_fpe_rows()     { toggleHiddenClass('fpe_row');     }
function update_pst12_rows()   { toggleHiddenClass('pst12_row');   }
function update_tpeg_rows()    { toggleHiddenClass('tpeg_row');    }
function update_pb_rows()      { toggleHiddenClass('pb_row');      }
function update_dtr_rows()     { toggleHiddenClass('dtr_row');     }
function update_urls_rows()    { toggleHiddenClass('urls_row');    }
