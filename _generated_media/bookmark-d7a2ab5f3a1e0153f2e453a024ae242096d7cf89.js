var jQueryScriptOutputted=false;function initJQuery(){if(typeof jQuery=="undefined"){if(!jQueryScriptOutputted){jQueryScriptOutputted=true;jq=document.createElement("SCRIPT");jq.type="text/javascript";jq.src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js";document.getElementsByTagName("head")[0].appendChild(jq);console.log("loading jquery")}setTimeout("initJQuery()",50)}else jQuery(function(){runScript()})}
function runScript(){(function(b){var a=document.createElement("div");a.innerHTML=b;document.body.appendChild(a.firstChild)})('<div id="tmpYupeat" style="position:absolute;padding-top:60px; width:100%; height:100%; min-height:3000px; border:0;top:0; right:0 bottom:0 left:0; z-index:9999; opacity:.98; background-color:#f2f2f2"><iframe src="'+("http://3.yupeat.appspot.com/order/popup?url="+encodeURIComponent(location.href))+'" frameBorder="0" width="100%" height="3000px" allowfullscreen></iframe><br><a id="tmpRemoveLink" onmouseover="this.style.backgroundColor = \'#D74F33\'; this.style.color=\'#FFF\'"onmouseout="this.style.backgroundColor = \'#FFF\'; this.style.color=\'#444\'"class="rmYupeat" style="position:fixed; z-index:10001; right:0;top:0; left:0; height:24px; padding:12px 0 0; text-align:center; font-family:Helvetica, Arial, sans-serif;font-size:14px; font-weight:bold; line-height:1em; color:#444; border-bottom:1px solid #ccc; -moz-box-shadow:0 0 2px #d7d7d7; -webkit-box-shadow:0 0 2px #d7d7d7; background:white; cursor:pointer; text-decoration:none;">Cancel Order</a></div>');
(function(){jQuery("#tmpRemoveLink").click(function(){jQuery("#tmpYupeat").remove()})})()}initJQuery();