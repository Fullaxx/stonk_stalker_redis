function toggleHidden(elementId)
{
  var e = document.getElementById(elementId)
  if (e.hidden) {
    e.removeAttribute("hidden");
  } else {
    e.setAttribute("hidden", true);
  }
}

function toggleGridHidden() { toggleHidden("ercalgrid"); }
function toggleListHidden() { toggleHidden("ercallist"); }

function market_calendars_init()
{

}