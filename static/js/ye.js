var lib = {
	gift:{
		init:function(){
			/*
			 * Handle gifts 
			 */
			
			function init_cc(){
				$("#stripeNumber0").watermark('Credit Card Number', {
					className: 'more-quiet'
				});
				
				$("#stripeCVC0").watermark('CVC Code', {
					className: 'more-quiet'
				});	
			}
			
			setTimeout(init_cc,250);
			
		}
	},
	vote:{
		init:function(){
			init_vote_handler();
			function init_vote_handler(){
				/*
				 * Handle votes 
				 */
				$('div.upvote').click(function(){
					var $this = $(this),
						count = $this.parent().parent().find('span.count').text();
					
					var	new_count = parseInt(count)+1;
						$this.parent().parent().find('span.count').html('<strong>'+new_count+'</strong>');
					
					var obj = {
						'vote_val': $this.attr('id')
					}
					
					$(this).css('background-image','none');
					
					$.ajax({
						async: true,
						cache: false,
						type: 'POST',
						data: obj,
						url: '/ajax/vote/',
						success: function(data){
							
						},                    
						error: function (xhr, ajaxOptions, thrownError){
						}		
					});
				});
				
				
				/*
				 * Show Attach Tooltip on click 
				 */
				
				$('#get_url-inactive').tipsy({
					gravity:'nw',
					trigger:'manual',
					title:function(){
						return $('#login-to-vote-url').html()
					},
					html:true,
					opacity:1.0
				});
				
				/*
				 * Show Login Tooltip on click 
				 */
				$('div.upvote-visible-inactive').click(function(){
					var rel = $(this).attr('rel');
					$(this).tipsy({
						gravity:'nw',
						trigger:'manual',
						title:function(){
							return $('#login-to-vote'+rel).html()
						},
						html:true,
						opacity:1.0
					});	
				})	
			}
			
			/*
			 * Watermarks on url form
			 */
			init_url();
			function init_url(){
				$("#url_val").watermark('http://', {
					className: 'more-quiet'
				});
			}
			
			/*
			 * Fetch name of website for attached url
			 */
			$("#get_url").click(function(event){
				event.preventDefault();
				var urlval = $("#url_val").val();
				
				$.get(urlval, function(res) { //get the html source of this website
				   		$('#get_url_placeholder').html($(res.responseText));
						var title = $('#get_url_placeholder').find('title').text();
						$('#get_url_placeholder').html('');
						$('#attach_url').hide();
						
						$('#id_name').val(title);
						$('#id_url').val(urlval);
						
						$('#vote_form').show();
				});
			});
			
			/*
			 * Sort Vote Results
			 */
			$("#vote-sort").click(function(event){
				event.preventDefault();
				var $target = $(event.target);
				
				if ($target.hasClass('filter')){
					var filtertype = $target.attr('id');
					var obj = {
						'filtertype': filtertype
					}
					
					$.ajax({
						async: true,
						cache: false,
						type: "POST",
						url: "/ajax/vote/filter/",
						data: obj,
						success: function(data){
							var str = data;
							$("#vote_list").html(str);
							$("#vote-sort>ul>li>a.active").removeClass("active");
							$target.addClass('active')
							init_vote_handler();
						},
						error: function(xhr, ajaxOptions, thrownError){
						}
						
					});	
				}
			});
			
			
							
			
		}
	},
	signup:{
		init:function(){
			var media_url = $('#media_url').val();
			$("#slides").slides({
					effect: 'fade',
					fadeSpeed: 350,
					pagination: true,
					play: 5000,
					crossfade: true,
					preload:true,
					preloadImage: '/'+media_url+'/images/loading.gif'
			});
			
			/*
			 * Ajax landing page code
			 */
			$("#landing_form").submit(function(event){
				event.preventDefault(); 
				
				var landing_form = $(event.target);
				
				$.ajax({
					async: true,
					cache: false,
					type: landing_form.attr('method'),
					url: '/profile/ajax/prospect/',
					data: landing_form.serialize(),
					success: function(data){
						var str = data;
						$("#x_signup").html(str);
						init_landing_page();
					},
					error:function (xhr, ajaxOptions, thrownError){
                    	/*console.log(xhr)*/
						/*console.log(thrownError)*/
						
						var $jstop = $('#js-messages-landing-top');
							
						$jstop.text('Enter valid email address');
						$jstop.show();
						
                	}                    
				});
				
			});
			
			
			/*
			 * Ajax login code / top and bottom of page
			 */
			init_landing_page();
			function init_landing_page(){
				$("#othercity_form").submit(function(event){
				event.preventDefault(); 
				
				var landing_form = $(event.target);
				
				$.ajax({
					async: true,
					cache: false,
					type: landing_form.attr('method'),
					url: '/profile/ajax/prospect/other/',
					data: landing_form.serialize(),
					success: function(data){
						var str = data;
						$("#x_signup").html(str);
					},
					error:function (xhr, ajaxOptions, thrownError){
                    	var $jstop = $('#js-messages-landing-top');
							
						$jstop.text('Enter valid email address');
						$jstop.show();
						
	                	}                    
					});
				});
				
				$("#cta_subscribe").click(function(event){
					event.preventDefault();
					var $subscribe = $(event.target);
					var city = $subscribe.attr('city');
					
					window.location.replace('/profile/subscribe/'+city);
					
				});
			
			}
		}
	},
	main: {
		init: function(){
			var $host = window.location.host
			/*if ($host != 'yupeat.appspot.com'){
				if (window.location.path){
					window.location = 'https://yupeat.appspot.com/'+ window.location.path;
					return	
				}
				else{
					window.location = 'https://yupeat.appspot.com/';
					return
				}
					
			}*/
			
			function getIP(){
				$.getJSON("http://jsonip.appspot.com?callback=?",
					function(data){
	   					saveIP(data.ip)			
					});
			}
			
			
			function getAddress(){
				
				var loc = {};
				var geocoder = new google.maps.Geocoder();
					
				if (google.loader.ClientLocation) {
					loc.lat = google.loader.ClientLocation.latitude;
					loc.lng = google.loader.ClientLocation.longitude;
					
					var latlng = new google.maps.LatLng(loc.lat, loc.lng);
					geocoder.geocode({
						'latLng': latlng
					}, function(results, status){
						if (status == google.maps.GeocoderStatus.OK) {
							var address = results[0]['formatted_address'];
							saveLocation(address);
						};
					});
				}
				else{
					saveLocation(null);
				}
			}
			
			google.load("maps", "3.x", {other_params: "sensor=false", callback:getAddress});
			
			function saveLocation(data){
				if (data == null) { getIP();}
				else{$.post('/ajax/location/', { address: data});}	
			}
			
			function saveIP(ipaddress){
				$.post('/ajax/ip/', {ip:ipaddress});
			}
			
			var $yr = $('#year').val(), 
				$mn = $('#month').val(),
				$dy = $('#day').val();
			
			$('#meal_expire').countdown({
				until: new Date($yr, $mn, $dy, 16, 30),
				timezone: -8,
				timeSeparator:' ',
				layout: '<div class="defaultCountdown right"><div class="time"><div class="hours numbers">{hnn}</div> '+
				'<div class="minutes numbers">{mnn}</div>'+
				'<div class="seconds numbers">{snn}</div></div>'+
				'<div class="countdown_tag"><p>{desc}</p></div></div>',
				compact: true,
				format: 'HMS',
				description:'hrs to order'
				});
			
		}
	},
	adminprofile: {
		init: function(){
			$(document).ready(function(){
			
			init_table_pagination();
			function init_table_pagination(){
				/*
				 * get url helper function
				 */
				function getUrlVars(anchor)
				{
				    var vars = [], hash;
				    var hashes = anchor.split('?');
				    
				    return hashes[1].split('=');
				}
				
				/*
				 * intercept next page request
				 */
				$("#page_next").click(function(event){
					event.preventDefault();
					var $target = $(event.target);
					
					var clicktype = $target.attr('id');
					var anchor = $target.attr('href');
					var page = getUrlVars(anchor)[1];
					
					var profiletab = $('#profile-tab').find('.tab.active').attr('id');
					
					var obj = {
						'profiletab': profiletab,
						'clicktype': clicktype,
						'page':page
					}
						
					$.ajax({
						async: true,
						cache: false,
						type: "POST",
						url: "/profile/ajax/admin/tablepage/",
						data: obj,
						success: function(data){
							var str = data;
							console.log(str);
							$("#table_content").html(str);
							init_table_pagination();
						},
						error: function(xhr, ajaxOptions, thrownError){
						}
						
					});
				})
				
				/*
				 * intercept prev page request
				 */
				$("#page_previous").click(function(event){
					event.preventDefault();
					var $target = $(event.target);
					
					var clicktype = $target.attr('id');
					
					var anchor = $target.attr('href');
					var page = getUrlVars(anchor)[1];
					
					var profiletab = $('#profile-tab').find('.tab.active').attr('id');
					
					var obj = {
						'profiletab': profiletab,
						'clicktype': clicktype,
						'page':page
					}
					
					$.ajax({
						async: true,
						cache: false,
						type: "POST",
						url: "/profile/ajax/admin/tablepage/",
						data: obj,
						success: function(data){
							var str = data;
							$("#table_content").html(str);
							init_table_pagination();
						},
						error: function(xhr, ajaxOptions, thrownError){
						}
						
					});
				})	
			}
			
			
			init_tab_handler();
			function init_tab_handler(){
				/*
			 * Swap profile views
			 */
			$("#profile-tab").click(function(event){
				event.preventDefault();
				var $target = $(event.target);
				
				if ($target.hasClass('tab')){
					var tabtype = $target.attr('id');
					var obj = {
						'profiletab': tabtype
					}
					
					$.ajax({
						async: true,
						cache: false,
						type: "POST",
						url: "/profile/ajax/admin/tab/",
						data: obj,
						success: function(data){
							var str = data;
							$("#table_content").html(str);
							$("#profile-tab>ul>li>a.active").removeClass("active");
							$target.addClass('active')
							
							init_tab_handler();
							init_table_pagination();
						},
						error: function(xhr, ajaxOptions, thrownError){
						}
						
						});	
					}
				});
			}
			
		})
	  }
	},
	schedule: {
		init: function(){
			$(document).ready(function(){
				var $meal_select = $('#meal_select')
				$meal_select.change(function(event){
					var $tr = $(event.target).closest('tr');
					var link = $tr.find('a').attr('href');
					var meal_val = $(event.target).val()
					
					$tr.find('a').attr('href',link+'?meal='+meal_val);
					
				})
			})
		}
	},
	order: {
		init: function(){
		$(document).ready(function(){
			
			/*
			 * Save Recipe
			 */
			init_saveRecipe();
			function init_saveRecipe(){
				$("#save-meal").click(function(){
					event.preventDefault();
					var obj = {
						'recipeid': $('#save-meal').val()
					}
					$.ajax({
						async: true,
						cache: false,
						type: 'POST',
						data: obj,
						url: '/order/ajax/remove-coupon/',
						success: function(data){
							/*Add alert message here */
						},
						error: function (xhr, ajaxOptions, thrownError){
						}        
					});
				}
			}


			/*
			 * Show/Hide Coupon Box
			 */
			init_showCoupon();
			function init_showCoupon(){
				$("#coupon").click(function(){
					$("#coupon_box").show();
					$(this).hide();
				});
				
				$("#cancel_coupon").click(function(){
					$("#coupon_box").hide();
					$("#coupon").show();
				});
			
			}
			
			/*
			 * Remove discount
			 *
			 */
			function init_removeCoupon(){
				$("#remove_coupon").click(function(){
					event.preventDefault();
					var obj = {
						'coupon_val': $('#confirm_coupon').val(),
						'total_val': $('#confirm_total').val()
					}
					$.ajax({
						async: true,
						cache: false,
						type: 'POST',
						data: obj,
						url: '/order/ajax/remove-coupon/',
						success: function(data){
							var str = data;
							$("#coupon_total_group").html(str);
							$("#totalbox_amount").text($("#confirm_total").val());
							init_showCoupon();
							init_applyCoupon();
						},                    
						error: function (xhr, ajaxOptions, thrownError){
						}		
					});
				})
			}
			
			/*
			 * Apply Coupon
			 *
			 */
			init_applyCoupon();
			function init_applyCoupon(){
				$("#coupon_submit").click(function(event){
					event.preventDefault();
					var obj = {
						'coupon_val': $('#coupon_entry').val(),
						'total_val': $('#confirm_total').val()
					}
					$.ajax({
						async: true,
						cache: false,
						type: 'POST',
						data: obj,
						url: '/order/ajax/apply-coupon/',
						success: function(data){
							var str = data;
							$("#coupon_total_group").html(str);
							$("#totalbox_amount").text($("#confirm_total").val());
							init_removeCoupon();
						},                    
						error: function (xhr, ajaxOptions, thrownError){
							$("#coupon_error").text('Invalid coupon code');
							$("#coupon_error").show();
						}		
					});
				});
			}
			
			
			
			/*
			 * Change location
			 */
			init_changeLocation();
			function init_changeLocation(){
				$("#change_location").click(function(event){
					event.preventDefault();
					$(this).hide();
					$("#new_location").show();
					init_newLocation();
				})
			}
			
			
			/*
			 * New Location initialization and ajax call
			 */
			function init_newLocation(){
				
				$("#new_location").change(function(){
					
					var obj = {
						'store_id': $(this).val(),
						'city':$(this).attr('city')
					}
					$.ajax({
						async: true,
						cache: false,
						type: 'POST',
						data: obj,
						url: '/order/ajax/change-location/',
						success: function(data){
							var str = data;
							var d = str.split("::");
										
							$("#location").html(d[0]);
							$("#items-for-purchase").html(d[1]);
							
							init_changeLocation();
							
							init_showCoupon();
							init_applyCoupon();
							init_removeCoupon();
							
							init_excluded();
							
						},                    
						error: function (xhr, ajaxOptions, thrownError){
							
						}
						
					});
				});
			}
			
			/*
			 * Watermarks on payment form
			 */
			
			function init_cc(){
				$("#stripeNumber0").watermark('Credit Card Number', {
					className: 'more-quiet'
				});
				
				$("#stripeCVC0").watermark('CVC Code', {
					className: 'more-quiet'
				});	
			}
			
			setTimeout(init_cc,250);
			
			init_order_page();
			function init_order_page(){
				$("#id_first_name").watermark('First Name', {className: 'more-quiet'});
				$("#id_last_name").watermark('Last Name', {className: 'more-quiet'});
				$("#id_street1").watermark('Street Address', {className: 'more-quiet'});
				$("#id_street2").watermark('Apt, Suite, Bldg (optional)', {className: 'more-quiet'});
				$("#id_city").watermark('City', {className: 'more-quiet'});
				$("#id_state").watermark('State', {className: 'more-quiet'});
				$("#id_postal_code").watermark('Postal Code', {className: 'more-quiet'});
				$("#id_card_number").watermark('Credit Card Number', {className: 'more-quiet'});
				$("#id_card_code").watermark('Security Code', {className: 'more-quiet'});	
				
				//Initialize storage
				$.Storage = new $.store();
				
				//Initialize excluded
				init_excluded();
				
				var $pu_time = $('#pickup_time')
				$pu_time.change(function(){
					ex_array[0] = $(this).val();
					$('#id_custom').val(ex_array);
				})
			
			}
			
			function init_excluded(){
				//Keeps track of excluded items
				//Used with paypal to pass variables through custom
				var ex_array = [1]
				function push_to_exculde(obj){
					var exists = include(ex_array, obj);
					ex_array.push(obj)
					
					//Save to local storage
					var ex_name = 'exclude_'+obj;
					$.Storage.set(ex_name,obj);
				};
				
				function pop_from_exculde(obj){
					var exists = include(ex_array, obj);
					if (exists != -1){
						ex_array.splice(exists,1)
					}
					
					//Remove from local storage
					if ($.Storage.get('exclude_'+obj)){
						$.Storage.del('exclude_'+obj)
					}
					
				};
				
				//Created an indexof function for IE6+
				if (!Array.prototype.indexOf) {
				  Array.prototype.indexOf = function (obj, fromIndex) {
				    if (fromIndex == null) {
				        fromIndex = 0;
				    } else if (fromIndex < 0) {
				        fromIndex = Math.max(0, this.length + fromIndex);
				    }
				    for (var i = fromIndex, j = this.length; i < j; i++) {
				        if (this[i] === obj)
				            return i;
				    }
				    return -1;
				  };
				}
				
				//Check if element is in array
				function include(arr,obj) {
    				if (arr.indexOf(obj) != -1){
						return arr.indexOf(obj);	
					}
					else{return -1}
				}
				
				
				//Creates default unchecked items
				var date = $('#date_now').val();
				if ($.Storage.get(date) === null){
					$.Storage.set(date,'True');
					$default_ex_items = $('input.excluded_items');
					
					$default_ex_items.each(function(i){
						var exitem = $(this).val();
						push_to_exculde(exitem)
					})
					
				}
				
				//Initialize any previously unchecked items
				var $init_items = $(".item_checkbox");
				$init_items.each(function(i){
					var $this = $(this);
					var $parent = $this.parent().parent();
					var item_name = $this.attr('name');
					if ($.Storage.get('exclude_'+item_name)){
						$this.attr('checked',false);
						$parent.find('div.item').addClass('strike');
						$parent.find('div.price').addClass('strike');
						
						push_to_exculde(item_name)
						
						var nv = parseFloat($('#total').text())-parseFloat($this.attr('price'));
						$('#total').text(nv.toFixed(2));
						$('#confirm_total').val(nv.toFixed(2));
						
						$('#totalbox_amount').text(nv.toFixed(2));
						$('#id_amount').val(nv.toFixed(2));
						
						$('#id_custom').val(ex_array);
					}
				});
				
				
				var $ingr = $('#ingredients');
				$ingr.click(function(e){
					var $target = $(e.target);
					if ($target.hasClass('item_checkbox')) {
					
						var total = $('#total').text(),
							price = $target.attr('price'), 
							newVal = 0.00, 
							$parent = $target.parent().parent();
						
						var itemDom = $parent.find('div.item'),
						    priceDom = $parent.find('div.price');
						
						if ($target.is(':checked')){
							new_val = parseFloat(total)+parseFloat(price);
							itemDom.removeClass('strike');
							priceDom.removeClass('strike');
							pop_from_exculde($target.attr('name'));
						} 
						else{
							new_val = parseFloat(total)-parseFloat(price);
							itemDom.addClass('strike');
							priceDom.addClass('strike');
							push_to_exculde($target.attr('name'));
						}
						
						$('#total').text(new_val.toFixed(2));
						$('#confirm_total').val(new_val.toFixed(2));
						
						
						$('#totalbox_amount').text(new_val.toFixed(2));
						$('#id_amount').val(new_val.toFixed(2));
						
						$('#id_custom').val(ex_array);  
				}
			})
			}
			
			})
		}
	},
	
	subscribe:{
		init:function(){
			$(document).ready(function(){
				
				function init_cc(){
				$("#stripeNumber0").watermark('Credit Card Number', {
					className: 'more-quiet'
				});
				
				$("#stripeCVC0").watermark('CVC Code', {
					className: 'more-quiet'
				});	
				}
			
				setTimeout(init_cc,250);
				
				$("#id_first_name").watermark('First Name', {className: 'more-quiet'});
				$("#id_last_name").watermark('Last Name', {className: 'more-quiet'});
				$("#id_street1").watermark('Street Address', {className: 'more-quiet'});
				$("#id_street2").watermark('Apt, Suite, Bldg (optional)', {className: 'more-quiet'});
				$("#id_city").watermark('City', {className: 'more-quiet'});
				$("#id_state").watermark('State', {className: 'more-quiet'});
				$("#id_postal_code").watermark('Postal Code', {className: 'more-quiet'});
				$("#id_card_number").watermark('Credit Card Number', {className: 'more-quiet'});
				$("#id_card_code").watermark('Security Code', {className: 'more-quiet'});
			})
		}
	},
	auth:{
		init:function(){
			$(document).ready(function(){
				init_auth();	
				function init_auth(){
					/*
					 * Open and close login window on top navigation
					 */
					$(".login_btn").click(function(e) {
		                e.preventDefault();
		                $("fieldset#signin_menu").toggle();
		                $(".login_btn").toggleClass("menu-open");
		            });
		
		            $("fieldset#signin_menu").mouseup(function() {
		                return false
		            });
					
					$(".logout_btn").click(function(e) {
		                e.preventDefault();
		                $("fieldset#signout_menu").toggle();
		                $(".logout_btn").toggleClass("menu-open");
		            });
					
					 $("fieldset#signout_menu").mouseup(function() {
		                return false
		            });
				}
				$(document).mouseup(function(e) {
				if($(e.target).parent("a.login_btn").length==0) {
                    $(".login_btn").removeClass("menu-open");
                    $("fieldset#signin_menu").hide();
                	}
            	});
			
			
			$(document).mouseup(function(e) {
				if($(e.target).parent("a.login_btn").length==0) {
                    $(".logout_btn").removeClass("menu-open");
                    $("fieldset#signout_menu").hide();
                }
            });
			
			/*
			 * Ajax login code / top and bottom of page
			 */
			
			$("#login_form").submit(function(event){
				event.preventDefault(); 
				var login_form = $(event.target);
				$.ajax({
					async: true,
					cache: false,
					type: login_form.attr('method'),
					url: '/profile/ajax/login/',
					data: login_form.serialize(),
					success: function(data){
						var str = data;
						var d = str.split("::");
						$("#login_block").html(d[0]);
						$("#payment").html(d[1]);
						init_order_page();
						init_auth();
						
						//reload page
						window.location.href=window.location.href;
					},
					error:function (xhr, ajaxOptions, thrownError){
                    	var $jstop = $('#js-messages-login-top'),
							$jsbottom = $('#js-messages-login-bottom');
							
						$jstop.text('Invalid password/username');
						$jsbottom.text('Invalid password/username');
						
						$jstop.show();
						$jsbottom.show();
                	}                    
				});
				
			});
			
			//TODO - Find a way to remove duplication of code
			init_order_page();
			function init_order_page(){
				var $fn = $('#billing_address').find('#id_first_name');
				var $ln = $('#billing_address').find('#id_last_name');
				
				$($fn).watermark('First Name', {
					className: 'more-quiet'
				});
				$($ln).watermark('Last Name', {
					className: 'more-quiet'
				});
				$("#id_street1").watermark('Street Address', {
					className: 'more-quiet'
				});
				$("#id_street2").watermark('Apt, Suite, Bldg (optional)', {
					className: 'more-quiet'
				});
				$("#id_city").watermark('City', {
					className: 'more-quiet'
				});
				$("#id_state").watermark('State', {
					className: 'more-quiet'
				});
				$("#id_postal_code").watermark('Postal Code', {
					className: 'more-quiet'
				});
				$("#id_card_number").watermark('Credit Card Number', {
					className: 'more-quiet'
				});
				$("#id_card_code").watermark('Security Code', {
					className: 'more-quiet'
				});
			
			}
			
			$("#sm_login_form").submit(function(event){
				event.preventDefault(); 
				
				var login_form = $(event.target);
				$.ajax({
					async: true,
					cache: false,
					type: login_form.attr('method'),
					url: '/profile/ajax/login/',
					data: login_form.serialize(),
					success: function(data, status){
						var str = data;
						var d = str.split("::");
						$("#login_block").html(d[0]);
						$("#payment").html(d[1]);
						init_order_page();
						init_auth();
						
						//Hide error messages
						 $('#js-messages-login-top').hide();
						$('#js-messages-login-bottom').hide();
						
						//reload page
						window.location = 'https://yupeat.appspot.com/order/sanfrancisco/'
					},
					error:function (xhr, ajaxOptions, thrownError){
                    	
						var $jstop = $('#js-messages-login-top'),
							$jsbottom = $('#js-messages-login-bottom');
							
						$jstop.text('Invalid password/username');
						$jsbottom.text('Invalid password/username');
						
						$jstop.show();
						$jsbottom.show();
                	}                   
				});
				
			 });
			 			
			});
		}
	}
}