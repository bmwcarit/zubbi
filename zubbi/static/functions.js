// Copyright 2018 BMW Car IT GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// To be able to use an api endpoint as source, it needs to accept a 'term'
// parameter containing the actual search item and must return a list of
// results (not wrapped into a dictionary or similar).
$('#zubbi-search').autocomplete({
  minLength: 3,
  delay: 500,
  source: '/api/search/autocomplete'
});

// Enable bootstrap tooltips
$(function(){
  $('[data-toggle="tooltip"]').tooltip()
})

// Toggle tabs on details page
$(function() {
    $(".nav-tabs a").click(function(e) {
        // Don't scroll to the anchors
        e.preventDefault();
        // Show the active tab and content
        $(this).tab("show");
    });
})

// Hide and show the advanced search box
$('#advancedSearchBoxShow').click(function(){
  $('#advancedSearchBox').show();
  $('#advancedSearchBoxShow').css('visibility','hidden');
  // Add hidden input to keep the advanced search open
  $('#advancedSearchBox').append('<input id="advancedInput" type="hidden" name="advanced" value="True">');
})

$('#advancedSearchBoxClose').click(function(){
  $('#advancedSearchBox').hide();
  $('#advancedSearchBoxShow').css('visibility','visible');
  // Remove the hidden input to close the advanced search
  $('#advancedInput').remove();
})

var urlParams = new URLSearchParams(window.location.search);
if(urlParams.has('advanced')) {
  $('#advancedSearchBox').append('<input id="advancedInput" type="hidden" name="advanced" value="True">');
}

function lmzify() {
    var fakeMouse = $("#fake-mouse");
    var inputField = $("#zubbi-search");
    var button = $("#zubbi-search-btn");
    var term = urlParams.get('term');

    // Calculate offsets for animations
    // NOTE (fschmidt): This is necessary, as the fake mouse has another parent
    // offset than the inputField. Thus, their 'starting' positions are both 0,
    // although they are at different places.
    var offsetInputX = inputField.offset().left - fakeMouse.offset().left + 15;
    var offsetInputY = inputField.offset().top - fakeMouse.offset().top + 10;

    var offsetButtonX = button.offset().left - inputField.offset().left;
    var offsetButtonY = button.offset().top - inputField.offset().top;

    var coverOffsetX = 10;
    var coverOffsetY = 40;

    // NOTE (fschmidt): Using display: none instead, results in wrong offset values
    // Thus, we are using visibility: 'hidden' and change it to 'visible' here
    fakeMouse.css('visibility', 'visible');
    // Move fake mouse relative to it's current position
    fakeMouse.animate({
        top: "+=" + offsetInputY,
        left: "+=" + offsetInputX
    }, 1500, 'swing', function() {
        // FIXME (fschmidt): Focus is not visible when using the browser
        // navigation (forward, back) to visit this page
        inputField.focus();
        // Move the cursor a little bit (to not cover the typing animation)
        fakeMouse.animate({
           top: "+=" + coverOffsetY,
           left: "+=" + coverOffsetX
        }, 500, 'swing', function() {
            var typed = new Typed('#zubbi-search', {
                strings: [term],
                typeSpeed: 100,
                onComplete: function() {
                    fakeMouse.animate({
                        top: "+=" + (offsetButtonY - coverOffsetY),
                        left: "+=" + (offsetButtonX - coverOffsetX)
                    }, 1500, 'swing', function() {
                        // Use focus to animate the button click
                        button.focus();
                        button.click();
                    });
                }
            });
        });
    });
}
