/*
*
======================================================================================
* ENHANCED WATER QUALITY EXPLORER WITH FFT & CROSS-CORRELATION (v20 - All Modes Enabled)
*
* Author: Enhanced by Claude & Gemini
* Last Updated: 2025-06-16
* Description: Integrated Fast Fourier Transform (FFT) for periodicity analysis
* and cross-correlation for comparing time-series relationships. This version
* enables advanced analysis for ROI, Transect, and Lake Level Height data.
======================================================================================
*/

// --- 1. INITIALIZE ENVIRONMENT ---
ui.root.clear();
var mainPanel = ui.Panel({ style: { stretch: 'both', backgroundColor: '#0d1117' } });
ui.root.add(mainPanel);

// --- GLOBAL VARIABLES ---
var globalImageCollection;
var globalGeometry;
var globalDateList;
var savedResults = {};
var comparisonMode = false;
var maxSavedResults = 10;
var currentAnalysisData = null;
var currentGeometry = null;


// --- CREATE MAIN LAYOUT ---
// Top toolbar panel
var toolbarPanel = ui.Panel({
  widgets: [],
  layout: ui.Panel.Layout.flow('horizontal'),
  style: {
    height: '60px',
    padding: '10px',
    border: '1px solid #cccccc'
  }
});
mainPanel.add(toolbarPanel);

// Add title and comparison toggle to toolbar
var titleLabel = ui.Label({
  value: '🌊 Water Quality Explorer Pro',
  style: {
    fontWeight: 'bold',
    fontSize: '24px',
    margin: '0 20px 0 0'
  }
});
toolbarPanel.add(titleLabel);

var comparisonToggle = ui.Button({
  label: '📊 Comparison Mode: OFF',
  onClick: function() {
    comparisonMode = !comparisonMode;
    comparisonToggle.setLabel('📊 Comparison Mode: ' + (comparisonMode ? 'ON' : 'OFF'));

    if (!comparisonMode) {
      print('⚠️ Comparison Mode OFF - New analyses will not be saved');
    } else {
      print('✅ Comparison Mode ON - Analyses will be saved automatically');
    }
  },
  style: {
    padding: '8px 16px',
    border: 'none'
  }
});
toolbarPanel.add(comparisonToggle);

// Create main content area with tabs
var contentPanel = ui.Panel({
  style: { stretch: 'both' }
});
mainPanel.add(contentPanel);

// Create tab panel
var tabPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('horizontal'),
  style: {

    padding: '0px',
    border: '1px solid #cccccc' // Corrected line
  }
});
contentPanel.add(tabPanel);

// Tab buttons
var tabs = {
  'analysis': ui.Button({
    label: '🔍 Analysis',
    style: {
      stretch: 'horizontal',
      // backgroundColor: null, // Default, active set by click handler
      color: '#495057',     // Default/inactive tab text color
      border: 'none',
      padding: '10px'
    }
  }),
  'comparison': ui.Button({
    label: '📈 Advanced Comparison',
    style: {
      stretch: 'horizontal',
      backgroundColor: '#e9ecef',
      color: '#495057',
      border: 'none',
      padding: '10px'
    }
  }),
  'history': ui.Button({
    label: '📚 History',
    style: {
      stretch: 'horizontal',
      backgroundColor: '#e9ecef',
      color: '#495057',
      border: 'none',
      padding: '10px'
    }
  }),
  'help': ui.Button({
    label: '❓ Help',
    style: {
      stretch: 'horizontal',
      backgroundColor: '#e9ecef',
      color: '#495057',
      border: 'none',
      padding: '10px'
    }
  })
};

// Tab content panels
var tabContents = {
  'analysis': ui.Panel({ style: { stretch: 'both', shown: true } }),
  'comparison': ui.Panel({ style: { stretch: 'both', shown: false } }),
  'history': ui.Panel({ style: { stretch: 'both', shown: false } }),
  'help': ui.Panel({ style: { stretch: 'both', shown: false } })
};

// BLOCK 1: A new, robust function to control which tab is visible.
function showTab(selectedKey) {
  // Loop through all the tab content panels and show only the selected one.
  for (var key in tabContents) {
    var isSelected = (key === selectedKey);
    tabContents[key].style().set('shown', isSelected);
    tabs[key].style().set('fontWeight', isSelected ? 'bold' : 'normal');
    tabs[key].style().set('color', isSelected ? '#212529' : '#495057');
  }
  // If the comparison tab is the one being displayed, update its list of saved items.
  if (selectedKey === 'comparison') {
    updateComparisonCheckboxes();
  }
}

// BLOCK 2: The new loop for setting up the tab clicks.
for (var tabKey in tabs) {
  (function(key) {
    tabPanel.add(tabs[key]);
    // When a tab is clicked, simply call our new showTab function.
    tabs[key].onClick(function() {
      showTab(key);
    });
  })(tabKey);
}

// Add tab contents
for (var tabKey in tabContents) {
  contentPanel.add(tabContents[tabKey]);
}

// --- ANALYSIS TAB CONTENT ---
var analysisSplitPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('horizontal'),
  style: { stretch: 'both' }
});
tabContents.analysis.add(analysisSplitPanel);

// Left panel for controls
var controlPanel = ui.Panel({
  style: {
    width: '380px',
    backgroundColor: '#f8f9fa',
    padding: '10px 15px',
    border: '1px solid #dee2e6'
  }
});
analysisSplitPanel.add(controlPanel);

// Right panel for map and charts
var visualizationPanel = ui.Panel({
  style: { stretch: 'both' }
});
analysisSplitPanel.add(visualizationPanel);

// Split visualization panel into map and chart areas
var mapChartSplit = ui.Panel({
  layout: ui.Panel.Layout.flow('horizontal'),
  style: { stretch: 'both' }
});
visualizationPanel.add(mapChartSplit);

var mapPanel = ui.Panel({ style: { stretch: 'both', width: '70%' } });
mapChartSplit.add(mapPanel);

var map = ui.Map();
map.setCenter(24.0, 38.5, 7);
map.setOptions('SATELLITE');
map.style().set('cursor', 'crosshair');
mapPanel.add(map);

// Chart panel (initially hidden)
var chartPanel = ui.Panel({
  style: {
    width: '30%',
    padding: '10px',
    shown: false,
    border: '1px solid #dee2e6'
  }
});
mapChartSplit.add(chartPanel);

// --- ENHANCED CONTROL PANEL ---
// Mode selection with better styling
var modePanel = ui.Panel({
  style: {
    padding: '10px',
    margin: '0 0 10px 0',
    border: '1px solid #999999',
    borderRadius: '8px'
  }
});
controlPanel.add(modePanel);

modePanel.add(ui.Label({
  value: '🎯 Select Analysis Mode',
  style: {
    fontWeight: 'bold',
    fontSize: '16px',
    margin: '0 0 10px 0'
  }
}));

var modeSelect = ui.Select({
  items: [
    'Ανάλυση Περιοχής (ROI)',
    'Ανάλυση Γραμμής (Transect)',
    'Ανάλυση Υψομέτρου Λίμνης'
  ],
  value: 'Ανάλυση Περιοχής (ROI)',
  onChange: function(mode) {
    updateUIForMode(mode);
  }
});

modePanel.add(modeSelect);

// --- Region Name Panel ---
var regionNamePanel = ui.Panel({
  style: {
    padding: '10px',
    margin: '0 0 10px 0',
  }
});
controlPanel.add(regionNamePanel);

regionNamePanel.add(ui.Label({
  value: '🏷️ Name Your Analysis Region',
  style: { fontWeight: 'bold', fontSize: '16px', margin: '0 0 10px 0' }
}));

var regionNameBox = ui.Textbox({
  placeholder: 'e.g., Lake Koroneia',
  value: 'My Analysis Area',
  style: {stretch: 'horizontal'}
});
regionNamePanel.add(regionNameBox);

// Instructions panel
var instructionPanel = ui.Panel({
  style: {
    backgroundColor: '#fff3cd',
    padding: '10px',
    margin: '10px 0',
    border: '1px solid #ffeeba',
    borderRadius: '8px'
  }
});
controlPanel.add(instructionPanel);

var instructionLabel = ui.Label({
  value: '1. Σχεδιάστε μια περιοχή (ROI).',
  style: { fontWeight: 'bold', color: '#856404' }
});
instructionPanel.add(instructionLabel);

// Date selection panel
var datePanel = ui.Panel({
  style: {
    padding: '10px',
    margin: '10px 0',
    borderRadius: '8px'
  }
});
controlPanel.add(datePanel);

datePanel.add(ui.Label({
  value: '📅 Χρονικό Εύρος',
  style: {
    fontWeight: 'bold',
    fontSize: '16px',
    margin: '0 0 10px 0'
  }
}));

var startDateBox = ui.Textbox({
  placeholder: 'YYYY-MM-DD',
  value: '2017-01-01'
});


var endDateBox = ui.Textbox({
  placeholder: 'YYYY-MM-DD',
  value: '2025-06-14'
});


datePanel.add(ui.Panel([
  ui.Label('Από:', { width: '50px', color: '#6c757d' }),
  startDateBox
], ui.Panel.Layout.flow('horizontal')));

datePanel.add(ui.Panel([
  ui.Label('Έως:', { width: '50px', color: '#6c757d' }),
  endDateBox
], ui.Panel.Layout.flow('horizontal')));

// Quick date presets
var presetPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('horizontal'),
  style: { margin: '10px 0' }
});

var presetButtons = [
  { label: '1Y', days: 365 },
  { label: '6M', days: 183 },
  { label: '3M', days: 91 },
  { label: '1M', days: 30 }
];

presetButtons.forEach(function(preset) {
  var btn = ui.Button({
    label: preset.label,
    onClick: function() {
      var end = new Date();
      var start = new Date(end.getTime() - preset.days * 24 * 60 * 60 * 1000);
      startDateBox.setValue(formatDate(start));
      endDateBox.setValue(formatDate(end));
    },
    style: {
      margin: '0 5px 0 0'
    }
  });
  presetPanel.add(btn);
});

datePanel.add(ui.Label('Γρήγορη επιλογή:', { fontSize: '12px' }));
datePanel.add(presetPanel);

// Parameter selection panel
var parameterPanel = ui.Panel({
  style: {
    padding: '10px',
    margin: '10px 0',
    border: '1px solid #c3e6cb',
    borderRadius: '8px',
    shown: true
  }
});
controlPanel.add(parameterPanel);

parameterPanel.add(ui.Label({
  value: '🔬 Παράμετρος Ποιότητας Νερού',
  style: {
    fontWeight: 'bold',
    fontSize: '16px',
    margin: '0 0 10px 0',
    color: '#212529'
  }
}));

var parameterSelect = ui.Select({
  items: [
    '--- Φυσικές Παράμετροι ---',
    'Water Surface Temperature - Θερμοκρασία Επιφάνειας (°C)',
    'True Color - Πραγματικό Χρώμα',
    '--- Βασικοί Δείκτες ---',
    'NDCI - Χλωροφύλλη',
    'NDTI - Θολότητα',
    'NDWI - Δείκτης Νερού',
    'GNIR - Λόγος Πράσινου/NIR',
    'CDOM - Χρωματισμένη Οργανική Ύλη',
    'TSM - Αιωρούμενα Στερεά',
    'Chl-a - Χλωροφύλλη-α (εκτίμηση)',
    'FAI - Floating Algae Index',
    '--- Ανίχνευση Μοτίβων ---',
    'Algae Bloom Detection - Ανίχνευση Ανθοφορίας',
    'Water Turbidity Classes - Κατηγορίες Θολότητας',
    'Anomaly Detection - Ανίχνευση Ανωμαλιών',
    '--- Se2WaQ Μοντέλα ---',
    'Chl-a (Se2WaQ) - Χλωροφύλλη-α',
    'Cya (Se2WaQ) - Κυανοβακτήρια',
    'Turb (Se2WaQ) - Θολότητα (NTU)',
    'CDOM (Se2WaQ) - Οργανική Ύλη',
    'DOC (Se2WaQ) - Διαλυμένος Άνθρακας',
    'Color (Se2WaQ) - Χρώμα Νερού'
  ],
  value: 'True Color - Πραγματικό Χρώμα'
});

parameterPanel.add(parameterSelect);

var paramWarningLabel = ui.Label('', {fontSize: '11px', color: '#856404', margin: '0 0 5px 5px'});
parameterPanel.add(paramWarningLabel);

// --- Data Source Selection Panel ---
var dataSourcePanel = ui.Panel({
  style: {
    padding: '10px',
    margin: '10px 0',
    border: '1px solid #b8daff',
    borderRadius: '5px'
  }
});
controlPanel.add(dataSourcePanel);

dataSourcePanel.add(ui.Label('📡 Επιλογή Πηγής Δεδομένων:', {
  fontWeight: 'bold',
  fontSize: '12px'
}));

var dataSourceSelect = ui.Select({
  items: [
    'L2A - Surface Reflectance (Προεπιλογή)',
    'L1C - Top of Atmosphere'
  ],
  value: 'L2A - Surface Reflectance (Προεπιλογή)'
});

dataSourcePanel.add(dataSourceSelect);

var dataSourceInfoLabel = ui.Label('ℹ️ L2A: Ατμοσφαιρικά διορθωμένα δεδομένα',
  {fontSize: '11px', margin: '5px 0'});
dataSourcePanel.add(dataSourceInfoLabel);

// Advanced settings for data source
var advancedDataPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {margin: '5px 0', shown: false}
});

var showAdvancedCheckbox = ui.Checkbox({
  label: '⚙️ Εμφάνιση προχωρημένων ρυθμίσεων',
  value: false,
  onChange: function(checked) {
    advancedDataPanel.style().set('shown', checked);
  }
});

dataSourcePanel.add(showAdvancedCheckbox);

var scalingFactorBox = ui.Textbox({
  placeholder: '10000',
  value: '10000'
});

advancedDataPanel.add(ui.Label('Παράγοντας κλιμάκωσης L1C:', {fontSize: '11px'}));
advancedDataPanel.add(scalingFactorBox);

var cloudMaskCheckbox = ui.Checkbox({
  label: 'Εφαρμογή μάσκας νεφών',
  value: true
});

advancedDataPanel.add(cloudMaskCheckbox);

dataSourcePanel.add(advancedDataPanel);

// Transect options (initially hidden)
var transectOptionsPanel = ui.Panel({style: {shown: false}});
controlPanel.add(transectOptionsPanel);

// Global variables for multi-transect support
var transectLines = [];
var transectLayers = [];
var nextTransectId = 1;

// Number of points input
var numPointsBox = ui.Textbox({
  placeholder: 'Αριθμός σημείων',
  value: '50'
});

transectOptionsPanel.add(ui.Label('1. Ρυθμίσεις Γραμμής:', {fontWeight: 'bold'}));
transectOptionsPanel.add(ui.Label('Αριθμός σημείων κατά μήκος της γραμμής:'));
transectOptionsPanel.add(numPointsBox);

// Transect management buttons
var buttonPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('horizontal'),
  style: {stretch: 'horizontal', margin: '10px 0'}
});

var addLineButton = ui.Button({
  label: '➕ Προσθήκη Τρέχουσας Γραμμής',
  onClick: function() {
    try {
      var geometry = drawingTools.layers().get(0).getEeObject();
      if (!geometry) {
        print('❌ Παρακαλώ σχεδιάστε πρώτα μια γραμμή.');
        return;
      }
      
      // Add new transect line with a unique color
      var color = getColorForIndex(transectLines.length);
      var transect = {
        id: 'transect_' + nextTransectId++,
        geometry: geometry,
        color: color,
        name: 'Γραμμή ' + transectLines.length
      };
      
      transectLines.push(transect);
      updateTransectList();
      
      // Add to map
      var layer = ui.Map.Layer(geometry, {color: color}, transect.name);
      map.layers().add(layer);
      transectLayers.push(layer);
      
      print('✅ Προστέθηκε νέα γραμμή: ' + transect.name);
    } catch(e) {
      print('❌ Σφάλμα κατά την προσθήκη γραμμής: ' + e);
    }
  },
  style: {stretch: 'horizontal', margin: '0 5px 0 0'}
});

var clearLinesButton = ui.Button({
  label: '❌ Καθαρισμός Όλων',
  onClick: function() {
    // Remove all transect layers from map
    transectLayers.forEach(function(layer) {
      map.layers().remove(layer);
    });
    transectLayers = [];
    transectLines = [];
    updateTransectList();
    print('✓ Καθαρίστηκαν όλες οι γραμμές');
  },
  style: {stretch: 'horizontal', margin: '0 0 0 5px'}
});

buttonPanel.add(addLineButton);
buttonPanel.add(clearLinesButton);
transectOptionsPanel.add(buttonPanel);

// Transect list panel
transectOptionsPanel.add(ui.Label('2. Λίστα Γραμμών:', {fontWeight: 'bold'}));

var transectListPanel = ui.Panel({
  style: {
    height: '200px',
    padding: '5px',
    backgroundColor: '#f8f9fa',
    border: '1px solid #dee2e6',
    margin: '5px 0 10px 0',
    position: 'relative',
    overflowY: 'auto'
  }
});
transectOptionsPanel.add(transectListPanel);

// Function to update the transect list UI
function updateTransectList() {
  transectListPanel.clear();
  
  if (transectLines.length === 0) {
    transectListPanel.add(ui.Label('Δεν υπάρχουν γραμμές', {color: '#6c757d'}));
    return;
  }
  
  transectLines.forEach(function(transect, index) {
    var itemPanel = ui.Panel({
      layout: ui.Panel.Layout.flow('horizontal'),
      style: {
        padding: '5px',
        margin: '2px 0',
        backgroundColor: index % 2 === 0 ? '#fff' : '#f8f9fa',
        border: '1px solid #dee2e6',
        borderRadius: '4px'
      }
    });
    
    var colorBox = ui.Label({
      value: '⬛',
      style: {color: transect.color, margin: '0 5px 0 0'}
    });
    
    var nameLabel = ui.Label({
      value: transect.name,
      style: {margin: '0 5px', flexGrow: 1}
    });
    
    var removeButton = ui.Button({
      label: '×',
      onClick: function() {
        // Remove from arrays
        var layer = transectLayers[index];
        map.layers().remove(layer);
        transectLayers.splice(index, 1);
        transectLines.splice(index, 1);
        updateTransectList();
      },
      style: {padding: '0 5px', margin: '0 0 0 5px'}
    });
    
    itemPanel.add(colorBox);
    itemPanel.add(nameLabel);
    itemPanel.add(removeButton);
    transectListPanel.add(itemPanel);
  });
}

// Lake Height options panel (initially hidden)
var lakeHeightOptionsPanel = ui.Panel({style: {shown: false}});
controlPanel.add(lakeHeightOptionsPanel);

lakeHeightOptionsPanel.add(ui.Label('3. Επιλογές Ανάλυσης Υψομέτρου:', {fontWeight: 'bold'}));

// Cloud coverage slider for lake height
var lakeCloudLabel = ui.Label('☁️ Μέγιστη Νεφοκάλυψη: 80%');
var lakeCloudSlider = ui.Slider({
  min: 0,
  max: 100,
  value: 80,
  step: 5,
  style: {stretch: 'horizontal'},
  onChange: function(value) {
    lakeCloudLabel.setValue('☁️ Μέγιστη Νεφοκάλυψη: ' + value + '%');
  }
});
lakeHeightOptionsPanel.add(lakeCloudLabel);
lakeHeightOptionsPanel.add(lakeCloudSlider);

// Water detection method selector for lake height
var lakeMethodLabel = ui.Label('🔍 Μέθοδος Ανίχνευσης Νερού:');
var lakeMethodSelect = ui.Select({
  items: ['Auto (Best)', 'NDWI Standard', 'MNDWI Enhanced', 'Multi-Index Fusion', 'AWEInsh', 'Simple Threshold'],
  value: 'Auto (Best)'
});

lakeHeightOptionsPanel.add(lakeMethodLabel);
lakeHeightOptionsPanel.add(lakeMethodSelect);

// Reference points toggle
var referencePointsCheckbox = ui.Checkbox({
  label: 'Εμφάνιση Σημείων Αναφοράς',
  value: false,
  style: {margin: '10px 0 0 0'}
});

lakeHeightOptionsPanel.add(referencePointsCheckbox);

// NDWI threshold slider for lake height
var lakeNdwiLabel = ui.Label('💧 Ευαισθησία Νερού: 0.00');
var lakeNdwiSlider = ui.Slider({
  min: -0.5,
  max: 0.5,
  value: 0.0,
  step: 0.05,
  style: {stretch: 'horizontal'},
  onChange: function(value) {
    lakeNdwiLabel.setValue('💧 Ευαισθησία Νερού: ' + value.toFixed(2));
  }
});
lakeHeightOptionsPanel.add(lakeNdwiLabel);
lakeHeightOptionsPanel.add(lakeNdwiSlider);

// Advanced options for lake height
var lakeAdvancedPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {margin: '10px 0', padding: '10px'}
});

var lakeAdvancedTitle = ui.Label('⚙️ Προχωρημένες Επιλογές', {fontWeight: 'bold'});
var lakeDebugCheckbox = ui.Checkbox('Εμφάνιση λεπτομερών πληροφοριών', false);


var lakePreprocessCheckbox = ui.Checkbox('Εφαρμογή μάσκας σκιών νεφών', true);


var lakeCompositeCheckbox = ui.Checkbox('Χρήση χρονικών σύνθετων', false);


lakeAdvancedPanel.add(lakeAdvancedTitle);
lakeAdvancedPanel.add(lakeDebugCheckbox);
lakeAdvancedPanel.add(lakePreprocessCheckbox);
lakeAdvancedPanel.add(lakeCompositeCheckbox);
lakeHeightOptionsPanel.add(lakeAdvancedPanel);

// Action buttons panel
var actionPanel = ui.Panel({
  style: {
    backgroundColor: '#e7f3ff',
    padding: '10px',
    margin: '10px 0',
    borderRadius: '8px',
    border: '1px solid #b8daff'
  }
});
controlPanel.add(actionPanel);

var runButton = ui.Button({
  label: '▶️ Εκτέλεση Ανάλυσης',
  onClick: function() {
    try {
      var geometry = drawingTools.layers().get(0).getEeObject();
      if (!geometry) {
        print('❌ Σφάλμα: Παρακαλώ σχεδιάστε πρώτα μια γεωμετρία στον χάρτη!');
        return;
      }
      currentGeometry = geometry;
      saveResultButton.style().set('shown', true);
      saveResultButton.setDisabled(true);
      saveResultButton.setLabel('💾 Γίνεται Ανάλυση...');
      loadData();
    } catch(e) {
      print('❌ Σφάλμα κατά την εκτέλεση: ' + e.toString());
    }
  },
  style: {
    stretch: 'horizontal',
    fontSize: '16px',
    padding: '10px'
  }
});
actionPanel.add(runButton);

// Save result button (shown after analysis)
var saveResultButton = ui.Button({
  label: '? Αποθήκευση Αποτελέσματος',
  onClick: function() {
    try {
      if (!currentAnalysisData || !currentGeometry) {
        print('❌ Παρακαλώ εκτελέστε πρώτα μια ανάλυση!');
        return;
      }
      if (!comparisonMode) {
        print('⚠️ Το Comparison Mode πρέπει να είναι ενεργοποιημένο για να αποθηκεύσετε αποτελέσματα!');
        return;
      }

      var areaName = regionNameBox.getValue();
      if (!areaName) {
        print('❌ Please provide a name for the analysis region.');
        return;
      }

      var finalizeSave = function(result) {
        if (!savedResults[areaName]) {
          savedResults[areaName] = { roi: [], transect: [], lakeHeight: [] };
        }

        var targetArray;
        if (result.type === 'ROI') { targetArray = savedResults[areaName].roi; }
        else if (result.type === 'Transect') { targetArray = savedResults[areaName].transect; }
        else if (result.type === 'Lake Height') { targetArray = savedResults[areaName].lakeHeight; }

        if (targetArray) {
          targetArray.push(result);
          if (targetArray.length > maxSavedResults) { targetArray.shift(); }
          updateHistoryList();
          print('✅ Αποθηκεύτηκε στο "' + areaName + '" (ID: ' + result.id + ')');
          saveResultButton.setDisabled(true);
          saveResultButton.setLabel('💾 Αποθηκεύτηκε');
        }
      };

      var mode = modeSelect.getValue();
      var parameter = (mode === 'Ανάλυση Υψομέτρου Λίμνης') ? 'Lake Height' : parameterSelect.getValue();
      var resultType;
      if (mode === 'Ανάλυση Περιοχής (ROI)') { resultType = 'ROI'; }
      else if (mode === 'Ανάλυση Γραμμής (Transect)') { resultType = 'Transect'; }
      else if (mode === 'Ανάλυση Υψομέτρου Λίμνης') { resultType = 'Lake Height'; }

      var result = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        areaName: areaName,
        mode: mode,
        type: resultType,
        parameter: parameter,
        dateRange: { start: startDateBox.getValue(), end: endDateBox.getValue() },
        geometry: currentGeometry,
        geometryType: mode,
        timeSeries: null // Add placeholder for standardized time series
      };

      if (mode === 'Ανάλυση Υψομέτρου Λίμνης') {
        print('📄 Evaluating Lake Height data before saving...');
        saveResultButton.setLabel('💾 Evaluating...');
        currentAnalysisData.elevationData.evaluate(function(evaluatedData, error) {
          if (error) {
            print('❌ Error saving lake height data: ' + error);
            saveResultButton.setLabel('💾 Save Failed').setDisabled(false);
          } else {
            // MODIFICATION START: Calculate and store the time series for Lake Height
            evaluatedData.features.forEach(function(f) {
              f.properties.date = new Date(f.properties['system:time_start']).toISOString().slice(0, 10);
            });
            result.data = evaluatedData; // Keep raw data for other charts
            
            print('📊 Extracting time series for Lake Height data...');
            var lakeHeightTimeSeries = evaluatedData.features.map(function(f) {
                if (f.properties.modelled_elevation !== null) {
                    return [f.properties.date, f.properties.modelled_elevation];
                }
                return null;
            }).filter(function(item) { return item !== null; }); // Filter out nulls

            result.timeSeries = lakeHeightTimeSeries;
            // MODIFICATION END
            finalizeSave(result);
          }
        });
      } else if (mode === 'Ανάλυση Περιοχής (ROI)') {
        saveResultButton.setLabel('💾 Collecting time series...');
        collectROITimeSeries(function(tsData) {
          result.data = tsData; 
          result.timeSeries = tsData; // Store standardized time series for ROI
          finalizeSave(result);
        });
      } else if (mode === 'Ανάλυση Γραμμής (Transect)') {
        // Calculate and store the average time series for the transect
        print('📊 Calculating average time series for transect...');
        var averageTimeSeries = [];
        var transectData = currentAnalysisData.data;
        var transectDates = currentAnalysisData.dates;
        var transectWater = currentAnalysisData.isWaterData;
        
        for (var i = 0; i < transectDates.length; i++) {
          var dailyValues = transectData[i];
          var dailyWaterFlags = transectWater[i];
          var waterValues = [];
          for (var j = 0; j < dailyValues.length; j++) {
            if(dailyWaterFlags[j] && dailyValues[j] !== null && !isNaN(dailyValues[j])) {
              waterValues.push(dailyValues[j]);
            }
          }
    
          if (waterValues.length > 0) {
            var sum = waterValues.reduce(function(a, b) { return a + b; }, 0);
            var average = sum / waterValues.length;
            averageTimeSeries.push([transectDates[i], average]);
          }
        }
        
        result.data = currentAnalysisData; // Keep raw data for heatmaps
        result.timeSeries = averageTimeSeries; // Store the new average time series
        finalizeSave(result);
      }
    } catch (e) {
      saveResultButton.setDisabled(false).setLabel('💾 Αποθήκευση Αποτελέσματος');
      print('❌ Σφάλμα κατά την αποθήκευση: ' + e.toString());
    }
  },
  style: { stretch: 'horizontal', fontSize: '14px', padding: '8px', shown: false },
  disabled: true
});
actionPanel.add(saveResultButton);

// Time slider panel
var sliderPanel = ui.Panel({style: {stretch: 'horizontal'}});
controlPanel.add(sliderPanel);

// Legend panel
var legendPanel = ui.Panel({style: {padding: '8px 15px'}});
controlPanel.add(legendPanel);

// Base map selector
var baseMapKeys = ['Google Satellite', 'Google Maps', 'Google Terrain'];
var mapSelector = ui.Select({
  items: baseMapKeys,
  value: 'Google Satellite',
  onChange: function(key) {
    if (key === 'Google Maps') { map.setOptions('ROADMAP'); }
    else if (key === 'Google Terrain') { map.setOptions('TERRAIN'); }
    else { map.setOptions('SATELLITE'); }
  }
});

controlPanel.add(ui.Label('Επιλογή Βασικού Χάρτη:', {fontWeight: 'bold', margin: '10px 0 0 0'}));
controlPanel.add(mapSelector);

// --- ADVANCED COMPARISON TAB CONTENT ---
var comparisonControlPanel = ui.Panel({
  style: {
    padding: '20px'
  }
});
tabContents.comparison.add(comparisonControlPanel);

comparisonControlPanel.add(ui.Label({
  value: '📊 Advanced Multi-Parameter Comparison',
  style: { fontWeight: 'bold', fontSize: '20px', margin: '0 0 20px 0' }
}));

// Comparison selection panel
var comparisonSelectionPanel = ui.Panel({
  style: {
    padding: '15px',
    borderRadius: '8px',
    margin: '0 0 20px 0'
  }
});
comparisonControlPanel.add(comparisonSelectionPanel);

comparisonSelectionPanel.add(ui.Label('Select Results to Compare:', {
  fontWeight: 'bold',
  margin: '0 0 10px 0'
}));

// Results selection checkboxes will be added dynamically
var resultCheckboxesPanel = ui.Panel({style: {}});
comparisonSelectionPanel.add(resultCheckboxesPanel);

// Comparison options
var comparisonOptionsPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('horizontal'),
  style: { margin: '10px 0' }
});
comparisonSelectionPanel.add(comparisonOptionsPanel);

var dualAxisCheckbox = ui.Checkbox({
  label: 'Enable Dual Y-Axis',
  value: true
});

comparisonOptionsPanel.add(dualAxisCheckbox);

var normalizeCheckbox = ui.Checkbox({
  label: 'Normalize Values (0-1)',
  value: false
});
comparisonOptionsPanel.add(normalizeCheckbox);

var compareButton = ui.Button({
  label: '🔄 Generate Comparison',
  onClick: generateAdvancedComparisonEnhanced, // Use the enhanced version
  style: {
    padding: '10px 20px',
    margin: '10px 0'
  }
});
comparisonSelectionPanel.add(compareButton);

// Comparison results panel
var comparisonResultsPanel = ui.Panel({
  style: {
    padding: '15px',
    borderRadius: '8px'
  }
});
tabContents.comparison.add(comparisonResultsPanel);

// --- HISTORY TAB CONTENT ---
var historyPanel = ui.Panel({
  style: { padding: '20px', backgroundColor: '#f8f9fa' }
});
tabContents.history.add(historyPanel);

historyPanel.add(ui.Label({
  value: '📚 Ιστορικό Αναλύσεων',
  style: { fontWeight: 'bold', fontSize: '20px', margin: '0 0 20px 0' }
}));

var historyListPanel = ui.Panel({style: {}});
historyPanel.add(historyListPanel);

// --- HELP TAB CONTENT ---
var helpPanel = ui.Panel({
  style: { padding: '20px', backgroundColor: '#f8f9fa' }
});
tabContents.help.add(helpPanel);

helpPanel.add(ui.Label({
  value: '❓ Οδηγός Χρήσης',
  style: { fontWeight: 'bold', fontSize: '20px', margin: '0 0 20px 0' }
}));

var helpText = '🎯 Οδηγός Γρήγορης Εκκίνησης:\n\n' +
  '1. Επιλέξτε Λειτουργία Ανάλυσης:\n' +
  '   • ROI: Ανάλυση συγκεκριμένης περιοχής\n' +
  '   • Transect: Ανάλυση κατά μήκος γραμμής\n' +
  '   • Υψόμετρο Λίμνης: Παρακολούθηση στάθμης λίμνης\n\n' +
  '2. Σχεδιάστε στον Χάρτη:\n' +
  '   • Χρησιμοποιήστε τα εργαλεία σχεδίασης\n' +
  '   • ROI: Σχεδιάστε πολύγωνο/ορθογώνιο\n' +
  '   • Transect: Σχεδιάστε γραμμή\n' +
  '   • Λίμνη: Σχεδιάστε γύρω από το όριο της λίμνης\n\n' +
  '3. Ορίστε Παραμέτρους:\n' +
  '   • Επιλέξτε χρονικό εύρος\n' +
  '   • Επιλέξτε παράμετρο ποιότητας νερού\n' +
  '   • Ρυθμίστε ειδικές επιλογές λειτουργίας\n\n' +
  '4. Εκτελέστε Ανάλυση:\n' +
  '   • Κλικ στο "Εκτέλεση Ανάλυσης"\n' +
  '   • Δείτε αποτελέσματα σε γραφήματα/χάρτες\n' +
  '   • Αποθηκεύστε για σύγκριση\n\n' +
  '5. Advanced Comparison:\n' +
  '   • Ενεργοποιήστε Comparison Mode (πράσινο)\n' +
  '   • Αποθηκεύστε πολλαπλές αναλύσεις\n' +
  '   • Επιλέξτε αποτελέσματα στην καρτέλα Comparison\n' +
  '   • Δημιουργήστε γραφήματα με dual y-axis\n' +
  '   • Συγκρίνετε διαφορετικές παραμέτρους\n\n' +
  'Συμβουλές:\n' +
  '• Χρησιμοποιήστε τα κουμπιά γρήγορης επιλογής ημερομηνίας\n' +
  '• Η γεωμετρία αποθηκεύεται μαζί με τα αποτελέσματα\n' +
  '• Μπορείτε να συγκρίνετε έως 5 παραμέτρους ταυτόχρονα\n' +
  '• Χρησιμοποιήστε normalize για σύγκριση διαφορετικών κλιμάκων';

helpPanel.add(ui.Label({
  value: helpText,
  style: { whiteSpace: 'pre-wrap', fontSize: '14px' }
}));

// --- DRAWING TOOLS SETUP ---
var drawingTools = map.drawingTools();

// --- HELPER FUNCTIONS ---
function formatDate(date) {
  var year = date.getFullYear();
  var month = ('0' + (date.getMonth() + 1)).slice(-2);
  var day = ('0' + date.getDate()).slice(-2);
  return year + '-' + month + '-' + day;
}

function updateUIForMode(mode) {
  try {
    // Clear existing drawings
    drawingTools.setShown(false);
    while (drawingTools.layers().length() > 0) {
      drawingTools.layers().remove(drawingTools.layers().get(0));
    }
    drawingTools.setShown(true);

    // Default visibility
    parameterSelect.style().set('shown', true);
    parameterPanel.style().set('shown', true);
    lakeHeightOptionsPanel.style().set('shown', false);
    transectOptionsPanel.style().set('shown', false);

    if (mode === 'Ανάλυση Περιοχής (ROI)') {
      drawingTools.setDrawModes(['polygon', 'rectangle']);
      instructionLabel.setValue('1. Σχεδιάστε μια περιοχή (ROI).');
      chartPanel.style().set('shown', false);
      mapPanel.style().set('width', '100%');
    } else if (mode === 'Ανάλυση Γραμμής (Transect)') {
      drawingTools.setDrawModes(['line']);
      instructionLabel.setValue('1. Σχεδιάστε μια γραμμή για ανάλυση transect.');
      chartPanel.style().set('shown', false);
      transectOptionsPanel.style().set('shown', true);
    } else if (mode === 'Ανάλυση Υψομέτρου Λίμνης') {
      drawingTools.setDrawModes(['polygon']);
      instructionLabel.setValue('1. Σχεδιάστε πολύγωνο γύρω από τη λίμνη.');
      chartPanel.style().set('shown', true);
      mapPanel.style().set('width', '70%');
      lakeHeightOptionsPanel.style().set('shown', true);
      parameterPanel.style().set('shown', false);
    }

    // Add a new empty layer for drawing
    var dummyGeometry = ui.Map.GeometryLayer({geometries: null, name: 'geometry', color: 'FF0000'});
    drawingTools.layers().add(dummyGeometry);
  } catch(e) {
    print('❌ Error in updateUIForMode: ' + e.toString());
  }
}

// --- ADVANCED COMPARISON FUNCTIONS ---
function getAllResults() {
  var allResults = [];
  for (var areaName in savedResults) {
    var areaData = savedResults[areaName];
    var process = function(result) {
      var newResult = JSON.parse(JSON.stringify(result));
      newResult.areaName = areaName;
      return newResult;
    };
    areaData.roi.forEach(function(r) { allResults.push(process(r)); });
    areaData.transect.forEach(function(r) { allResults.push(process(r)); });
    areaData.lakeHeight.forEach(function(r) { allResults.push(process(r)); });
  }
  return allResults;
}

function updateComparisonCheckboxes() {
  resultCheckboxesPanel.clear();
  if (Object.keys(savedResults).length === 0) {
    resultCheckboxesPanel.add(ui.Label('No saved results available.'));
    return;
  }

  for (var areaName in savedResults) {
    var areaData = savedResults[areaName];
    resultCheckboxesPanel.add(ui.Label('📍 ' + areaName, {
      fontWeight: 'bold', color: '#007bff', margin: '15px 0 5px 0', border: '1px solid #ddd', padding: '4px'
    }));

    var addCheckboxes = function(results) {
      results.forEach(function(result) {
        var label = result.type + ': ' + (result.parameter.split(' - ')[0]) + ' (' + result.dateRange.start + ' - ' + result.dateRange.end + ')';
        var checkbox = ui.Checkbox(label, false);
        checkbox.resultData = result;
        resultCheckboxesPanel.add(checkbox);
      });
    };

    addCheckboxes(areaData.roi);
    addCheckboxes(areaData.transect);
    addCheckboxes(areaData.lakeHeight);
  }
}

function updateHistoryList() {
  historyListPanel.clear();
  var allResults = getAllResults();
  allResults.sort(function(a, b) { return new Date(b.timestamp) - new Date(a.timestamp); });

  if (allResults.length === 0) {
    historyListPanel.add(ui.Label('Δεν υπάρχει ιστορικό αναλύσεων ακόμα'));
    return;
  }

  allResults.forEach(function(result, index) {
    var historyItem = ui.Panel({
      layout: ui.Panel.Layout.flow('vertical'),
      style: { padding: '10px', margin: '5px 0', border: '1px solid #dee2e6', borderRadius: '4px' }
    });

    var title = '🏷️ ' + result.areaName + ': ' + result.type + ' - ' + result.parameter.split(' - ')[0];
    historyItem.add(ui.Label(title, {fontWeight: 'bold'}));
    historyItem.add(ui.Label(new Date(result.timestamp).toLocaleString('el-GR'), {fontSize: '11px', color: '#6c757d'}));

    var buttonPanel = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: {margin: '5px 0 0 0'} });
    var viewButton = ui.Button({ label: 'Προβολή', onClick: function() { loadSavedResult(result); }, style: { margin: '0 5px 0 0' } });
    var deleteButton = ui.Button({ label: 'Διαγραφή', onClick: function() { deleteSavedResult(result); }});
    buttonPanel.add(viewButton).add(deleteButton);
    historyItem.add(buttonPanel);

    historyListPanel.add(historyItem);
  });
}

// Corrected function to handle data types explicitly
function createCombinedComparisonChart(results) {
  var chartPanel = ui.Panel({
    style: { padding: '15px', borderRadius: '8px', margin: '15px 0', backgroundColor: '#ffffff', border: '1px solid #dee2e6' }
  });
  comparisonResultsPanel.add(chartPanel);

  var dataTable = [['Date']];
  var seriesOptions = {};
  var seriesColors = [];
  var vAxes = {};
  var axisCount = 0;
  var unitAxisMap = {};

  // 1. Build Header and configure series options
  results.forEach(function(result, index) {
    var seriesName = result.parameter.split(' - ')[0] + ' (' + result.areaName + ' - ' + result.type + ')';
    dataTable[0].push(seriesName);
    seriesColors.push(getColorForIndex(index));

    var unit = result.type === 'Lake Height' ? 'm' : result.parameter;

    if (unitAxisMap[unit] === undefined) {
      unitAxisMap[unit] = axisCount;
      vAxes[axisCount] = { title: result.type === 'Lake Height' ? 'Υψόμετρο (m)' : 'Τιμή' };
      axisCount++;
    }
    seriesOptions[index] = { targetAxisIndex: unitAxisMap[unit] };

    if (result.type === 'Lake Height') {
      seriesOptions[index].type = 'line';
      seriesOptions[index].pointSize = 5;
      seriesOptions[index].lineWidth = 1.5;
    } else {
      seriesOptions[index].type = 'line';
    }
  });

  // 2. Gather all unique dates from all results
  var allDates = [];
  results.forEach(function(result) {
    try {
      if (result.timeSeries) { // Use the standardized time series if it exists
        result.timeSeries.forEach(function(dp) { if (dp[0] && allDates.indexOf(dp[0]) === -1) allDates.push(dp[0]); });
      } else if (result.type === 'Lake Height' && result.data && result.data.features) { // Fallback for Lake Height
        result.data.features.forEach(function(feature) {
          var dateStr = feature.properties.date;
          if (dateStr && allDates.indexOf(dateStr) === -1) {
            allDates.push(dateStr);
          }
        });
      }
    } catch(e) { print('Error processing dates for result: ', result); }
  });
  allDates.sort(function(a, b) { return new Date(a) - new Date(b); });

  // 3. Populate the data rows with improved data handling
  allDates.forEach(function(dateStr) {
    var row = [new Date(dateStr)];
    results.forEach(function(result) {
      var value = null;
      var rawValue = null;

      try {
        if (result.timeSeries) { // Prioritize the standardized time series
          var dataPoint = result.timeSeries.find(function(dp) { return dp && dp[0] === dateStr; });
          if (dataPoint) rawValue = dataPoint[1];
        } else if (result.type === 'Lake Height' && result.data && result.data.features) { // Fallback for Lake Height
          var dataPoint = result.data.features.find(function(f) { return f.properties.date === dateStr; });
          if (dataPoint && dataPoint.properties.modelled_elevation !== null) {
            rawValue = Number(dataPoint.properties.modelled_elevation);
          }
        }

        // Filter for valid, realistic values
        if (rawValue !== null && !isNaN(rawValue)) {
          if (result.parameter.indexOf('Temperature') > -1) {
            if (rawValue >= 0 && rawValue <= 40) {
              value = rawValue;
            }
          } else {
            value = rawValue; 
          }
        }
      } catch(e) { print('Error processing data row for result: ', result); }

      row.push(value);
    });
    dataTable.push(row);
  });

  if (dataTable.length <= 1) {
    chartPanel.add(ui.Label('Δεν βρέθηκαν δεδομένα για σύγκριση.', {padding: '10px'}));
    return;
  }

  // 4. Create and display the Combo Chart
  var chartOptions = {
    title: 'Συνδυασμένη Σύγκριση Πολλαπλών Αξόνων',
    vAxes: vAxes,
    hAxis: { title: 'Ημερομηνία', titleTextStyle: { color: '#333333' } },
    series: seriesOptions,
    colors: seriesColors,
    interpolateNulls: true,
    height: 500,
    legend: { position: 'top' },
    chartArea: {backgroundColor: '#f8f9fa'},
    explorer: {
      actions: ['dragToZoom', 'rightClickToReset'],
      axis: 'horizontal',
      keepInBounds: true,
      maxZoomIn: 8.0
    }
  };

  var comboChart = ui.Chart(dataTable)
                       .setChartType('ComboChart')
                       .setOptions(chartOptions);

  chartPanel.add(comboChart);
}


function visualizeComparisonGeometries(results) {
  try {
    // Clear existing layers except base
    while (map.layers().length() > 1) {
      map.layers().remove(map.layers().get(1));
    }

    // Add each geometry with different colors
    results.forEach(function(result, index) {
      if (result.geometry) {
        var color = getColorForIndex(index);
        var layer = ui.Map.Layer(result.geometry,
          { color: color },
          result.parameter.split(' - ')[0] + ' (' + result.type + ')'
        );
        map.layers().add(layer);
      }
    });

    // Center map on first geometry
    if (results[0] && results[0].geometry) {
      map.centerObject(results[0].geometry, 12);
    }

    print('✅ Geometries visualized on map');
  } catch(e) {
    print('❌ Error visualizing geometries: ' + e.toString());
  }
}

function getColorForIndex(index) {
  var colors = ['#007bff', '#28a745', '#ffc107', '#6f42c1', '#dc3545'];
  return colors[index % colors.length];
}


// ===== START: INTEGRATED ANALYSIS FUNCTIONS =====

// ===== FFT ANALYSIS FUNCTIONS =====

/**
 * Discrete Fourier Transform implementation
 * Since mathjs is not available in GEE, we implement a basic DFT
 */
function computeDFT(signal) {
  var N = signal.length;
  var frequencies = [];
  var magnitudes = [];
  var phases = [];

  // Compute DFT for each frequency bin
  for (var k = 0; k < N/2; k++) {
    var sumReal = 0;
    var sumImag = 0;

    for (var n = 0; n < N; n++) {
      var angle = -2 * Math.PI * k * n / N;
      sumReal += signal[n] * Math.cos(angle);
      sumImag += signal[n] * Math.sin(angle);
    }

    var magnitude = Math.sqrt(sumReal * sumReal + sumImag * sumImag) / N;
    var phase = Math.atan2(sumImag, sumReal);

    frequencies.push(k);
    magnitudes.push(magnitude);
    phases.push(phase);
  }

  return {
    frequencies: frequencies,
    magnitudes: magnitudes,
    phases: phases,
    N: N
  };
}

/**
 * Compute power spectral density from time series
 */
function computePowerSpectrum(timeSeries, samplingRate) {
  // Remove mean (detrending)
  var mean = timeSeries.reduce(function(a, b) { return a + b; }, 0) / timeSeries.length;
  var detrendedSignal = timeSeries.map(function(x) { return x - mean; });

  // Apply Hamming window to reduce spectral leakage
  var windowedSignal = detrendedSignal.map(function(x, i) {
    var w = 0.54 - 0.46 * Math.cos(2 * Math.PI * i / (detrendedSignal.length - 1));
    return x * w;
  });

  // Compute DFT
  var dft = computeDFT(windowedSignal);

  // Convert to actual frequencies and power
  var actualFrequencies = dft.frequencies.map(function(f) {
    return f * samplingRate / dft.N;
  });

  var power = dft.magnitudes.map(function(m) {
    return m * m; // Power is magnitude squared
  });

  return {
    frequencies: actualFrequencies,
    power: power,
    magnitudes: dft.magnitudes
  };
}

/**
 * Find dominant frequencies in the spectrum
 */
function findDominantFrequencies(spectrum, numPeaks) {
  numPeaks = numPeaks || 3;

  // Create array of frequency-power pairs
  var pairs = [];
  for (var i = 1; i < spectrum.frequencies.length; i++) { // Skip DC component
    pairs.push({
      frequency: spectrum.frequencies[i],
      power: spectrum.power[i],
      period: 1 / spectrum.frequencies[i] // Period in days
    });
  }

  // Sort by power
  pairs.sort(function(a, b) { return b.power - a.power; });

  // Return top peaks
  return pairs.slice(0, numPeaks);
}

/**
 * Create FFT analysis panel for a time series
 */
function createFFTAnalysisPanel(timeSeries, dates, parameter, parentPanel) {
  var fftPanel = ui.Panel({
    style: {
      padding: '15px',
      margin: '10px 0',
      border: '1px solid #dee2e6',
      borderRadius: '8px',
      backgroundColor: '#f8f9fa'
    }
  });

  fftPanel.add(ui.Label({
    value: '📊 FFT Analysis: ' + parameter,
    style: { fontWeight: 'bold', fontSize: '16px', margin: '0 0 10px 0' }
  }));

  // Calculate sampling rate (days between samples)
  var avgSamplingDays = 0;
  if (dates.length > 1) {
    var totalDays = 0;
    for (var i = 1; i < dates.length; i++) {
      var days = (new Date(dates[i]) - new Date(dates[i-1])) / (1000 * 60 * 60 * 24);
      totalDays += days;
    }
    avgSamplingDays = totalDays / (dates.length - 1);
  }

  var samplingRate = 1 / avgSamplingDays; // Samples per day

  // Compute spectrum
  var spectrum = computePowerSpectrum(timeSeries, samplingRate);
  var dominantFreqs = findDominantFrequencies(spectrum, 5);

  // Create frequency spectrum chart
  var chartData = [['Frequency (1/days)', 'Power']];
  for (var i = 0; i < spectrum.frequencies.length; i++) {
    if (spectrum.frequencies[i] > 0 && spectrum.frequencies[i] < 0.5) { // Limit to meaningful range
      chartData.push([spectrum.frequencies[i], spectrum.power[i]]);
    }
  }
  
  // FIX: Check if there is data to plot before creating the chart
  if (chartData.length <= 1) {
    fftPanel.add(ui.Label('Could not generate power spectrum. No significant frequencies found in the display range.', {
      padding: '10px',
      backgroundColor: '#fff3cd',
      color: '#856404'
    }));
  } else {
    var spectrumChart = ui.Chart(chartData, 'LineChart').setOptions({
      title: 'Power Spectrum',
      hAxis: {
        title: 'Frequency (cycles/day)',
        scaleType: 'log',
        textStyle: { color: '#333333' },
        titleTextStyle: { color: '#333333' }
      },
      vAxis: {
        title: 'Power',
        scaleType: 'log',
        textStyle: { color: '#333333' },
        titleTextStyle: { color: '#333333' }
      },
      colors: ['#dc3545'],
      height: 300,
      backgroundColor: '#ffffff',
      legend: 'none'
    });
    fftPanel.add(spectrumChart);
  }

  // Display dominant frequencies
  var freqPanel = ui.Panel({
    style: {
      padding: '10px',
      backgroundColor: '#e9ecef',
      borderRadius: '4px',
      margin: '10px 0'
    }
  });

  freqPanel.add(ui.Label('🎯 Dominant Periods:', { fontWeight: 'bold' }));

  dominantFreqs.forEach(function(freq, index) {
    var periodDays = freq.period;
    var periodText;

    if (periodDays > 365) {
      periodText = (periodDays / 365).toFixed(1) + ' years';
    } else if (periodDays > 30) {
      periodText = (periodDays / 30).toFixed(1) + ' months';
    } else if (periodDays > 7) {
      periodText = (periodDays / 7).toFixed(1) + ' weeks';
    } else {
      periodText = periodDays.toFixed(1) + ' days';
    }

    freqPanel.add(ui.Label((index + 1) + '. ' + periodText + ' (Power: ' + freq.power.toFixed(4) + ')', {
      fontSize: '12px',
      color: '#495057'
    }));
  });

  fftPanel.add(freqPanel);
  parentPanel.add(fftPanel);
}

// ===== CROSS-CORRELATION FUNCTIONS =====

/**
 * Compute cross-correlation between two signals
 */
function crossCorrelation(signal1, signal2, maxLag) {
  maxLag = maxLag || Math.floor(signal1.length / 4);
  var correlations = [];
  var lags = [];

  // Normalize signals
  var mean1 = signal1.reduce(function(a, b) { return a + b; }, 0) / signal1.length;
  var mean2 = signal2.reduce(function(a, b) { return a + b; }, 0) / signal2.length;

  var norm1 = signal1.map(function(x) { return x - mean1; });
  var norm2 = signal2.map(function(x) { return x - mean2; });

  var std1 = Math.sqrt(norm1.reduce(function(a, b) { return a + b * b; }, 0) / norm1.length);
  var std2 = Math.sqrt(norm2.reduce(function(a, b) { return a + b * b; }, 0) / norm2.length);

  // Compute correlation for each lag
  for (var lag = -maxLag; lag <= maxLag; lag++) {
    var sum = 0;
    var count = 0;

    for (var i = 0; i < signal1.length; i++) {
      var j = i + lag;
      if (j >= 0 && j < signal2.length) {
        sum += norm1[i] * norm2[j];
        count++;
      }
    }

    if (count > 0 && std1 > 0 && std2 > 0) {
      var correlation = sum / (count * std1 * std2);
      correlations.push(correlation);
      lags.push(lag);
    }
  }

  return {
    correlations: correlations,
    lags: lags,
    maxCorrelation: Math.max.apply(null, correlations.map(Math.abs)),
    maxCorrelationLag: lags[correlations.map(Math.abs).indexOf(Math.max.apply(null, correlations.map(Math.abs)))]
  };
}

/**
 * Interpolate time series to common time grid
 */
function interpolateToCommonGrid(series1, dates1, series2, dates2) {
  // Find common date range
  var startDate = new Date(Math.max(new Date(dates1[0]), new Date(dates2[0])));
  var endDate = new Date(Math.min(new Date(dates1[dates1.length - 1]), new Date(dates2[dates2.length - 1])));

  // Create common time grid (daily)
  var commonDates = [];
  var currentDate = new Date(startDate);
  while (currentDate <= endDate) {
    commonDates.push(currentDate.toISOString().split('T')[0]);
    currentDate.setDate(currentDate.getDate() + 1);
  }

  // Linear interpolation function
  function interpolate(dates, values, targetDate) {
    var targetTime = new Date(targetDate).getTime();

    for (var i = 0; i < dates.length - 1; i++) {
      var time1 = new Date(dates[i]).getTime();
      var time2 = new Date(dates[i + 1]).getTime();

      if (targetTime >= time1 && targetTime <= time2) {
        var t = (targetTime - time1) / (time2 - time1);
        return values[i] + t * (values[i + 1] - values[i]);
      }
    }
    
    // If we get here, the target date is outside our date range
    return null;
  }

  // Interpolate both series
  var interpolated1 = [];
  var interpolated2 = [];

  commonDates.forEach(function(date) {
    var val1 = interpolate(dates1, series1, date);
    var val2 = interpolate(dates2, series2, date);

    if (val1 !== null && val2 !== null) {
      interpolated1.push(val1);
      interpolated2.push(val2);
    }
  });

  return {
    series1: interpolated1,
    series2: interpolated2,
    dates: commonDates
  };
}

/**
 * Create cross-correlation analysis panel
 */
function createCrossCorrelationPanel(result1, result2, parentPanel) {
  var xcorrPanel = ui.Panel({
    style: {
      padding: '15px',
      margin: '10px 0',
      border: '2px solid #007bff',
      borderRadius: '8px',
      backgroundColor: '#f8f9fa'
    }
  });

  xcorrPanel.add(ui.Label({
    value: '🔗 Cross-Correlation Analysis',
    style: { fontWeight: 'bold', fontSize: '18px', margin: '0 0 15px 0', color: '#007bff' }
  }));

  // Extract standardized time series data
  var series1, dates1, series2, dates2;

  if (result1.timeSeries) {
    dates1 = result1.timeSeries.map(function(d) { return d[0]; });
    series1 = result1.timeSeries.map(function(d) { return d[1]; });
  }

  if (result2.timeSeries) {
    dates2 = result2.timeSeries.map(function(d) { return d[0]; });
    series2 = result2.timeSeries.map(function(d) { return d[1]; });
  }

  if (!series1 || !series2 || series1.length < 10 || series2.length < 10) {
    xcorrPanel.add(ui.Label('⚠️ Insufficient data for cross-correlation analysis', {
      color: '#856404'
    }));
    parentPanel.add(xcorrPanel);
    return;
  }

  // Interpolate to common grid
  var interpolated = interpolateToCommonGrid(series1, dates1, series2, dates2);

  // Compute cross-correlation
  var maxLag = Math.min(90, Math.floor(interpolated.series1.length / 4)); // Max 90 days lag
  var xcorr = crossCorrelation(interpolated.series1, interpolated.series2, maxLag);

  // Create correlation plot
  var chartData = [['Lag (days)', 'Correlation']];
  for (var i = 0; i < xcorr.lags.length; i++) {
    chartData.push([xcorr.lags[i], xcorr.correlations[i]]);
  }

  if (chartData.length <= 1) {
    xcorrPanel.add(ui.Label('⚠️ Could not compute correlation. The time series may not overlap or contain valid data.', {
      color: '#856404'
    }));
  } else {
    var xcorrChart = ui.Chart(chartData, 'LineChart').setOptions({
      title: result1.parameter.split(' - ')[0] + ' vs ' + result2.parameter.split(' - ')[0],
      hAxis: {
        title: 'Lag (days)',
        textStyle: { color: '#333333' },
        titleTextStyle: { color: '#333333' }
      },
      vAxis: {
        title: 'Correlation Coefficient',
        viewWindow: { min: -1, max: 1 },
        textStyle: { color: '#333333' },
        titleTextStyle: { color: '#333333' }
      },
      colors: ['#28a745'],
      height: 300,
      backgroundColor: '#ffffff',
      hAxis: {
        gridlines: { count: 7 }
      },
      vAxis: {
        gridlines: { count: 5 }
      }
    });
    xcorrPanel.add(xcorrChart);
  }


  // Display results
  var resultsPanel = ui.Panel({
    style: {
      padding: '10px',
      backgroundColor: '#e7f3ff',
      borderRadius: '4px',
      margin: '10px 0'
    }
  });

  resultsPanel.add(ui.Label('📊 Results:', { fontWeight: 'bold' }));
  resultsPanel.add(ui.Label('Maximum Correlation: ' + xcorr.maxCorrelation.toFixed(3), {
    fontSize: '14px',
    color: '#004085'
  }));
  resultsPanel.add(ui.Label('Lag at Max Correlation: ' + xcorr.maxCorrelationLag + ' days', {
    fontSize: '14px',
    color: '#004085'
  }));

  // Interpret the correlation
  var interpretation;
  var absCorr = Math.abs(xcorr.maxCorrelation);

  if (absCorr > 0.7) {
    interpretation = 'Strong correlation';
  } else if (absCorr > 0.5) {
    interpretation = 'Moderate correlation';
  } else if (absCorr > 0.3) {
    interpretation = 'Weak correlation';
  } else {
    interpretation = 'Very weak or no correlation';
  }

  resultsPanel.add(ui.Label('Interpretation: ' + interpretation, {
    fontSize: '14px',
    fontWeight: 'bold',
    color: absCorr > 0.5 ? '#155724' : '#856404'
  }));

  if (xcorr.maxCorrelationLag !== 0) {
    var leadLag = xcorr.maxCorrelationLag > 0 ?
      result1.parameter.split(' - ')[0] + ' leads ' + result2.parameter.split(' - ')[0] :
      result2.parameter.split(' - ')[0] + ' leads ' + result1.parameter.split(' - ')[0];

    resultsPanel.add(ui.Label('Lead/Lag: ' + leadLag + ' by ' + Math.abs(xcorr.maxCorrelationLag) + ' days', {
      fontSize: '12px',
      color: '#6c757d'
    }));
  }

  xcorrPanel.add(resultsPanel);
  parentPanel.add(xcorrPanel);
}

// ===== ENHANCED COMPARISON FUNCTION WITH FFT AND CROSS-CORRELATION =====
function generateAdvancedComparisonEnhanced() {
  try {
    comparisonResultsPanel.clear();

    var selectedResults = [];
    var allWidgets = resultCheckboxesPanel.widgets();

    // Find checked boxes
    for (var i = 0; i < allWidgets.length(); i++) {
      var widget = allWidgets.get(i);
      if (widget.getValue && typeof widget.getValue === 'function' &&
          widget.getValue() === true && widget.resultData) {
        selectedResults.push(widget.resultData);
      }
    }

    if (selectedResults.length === 0) {
      comparisonResultsPanel.add(ui.Label('⚠️ Please select at least one result for comparison.', {
        color: '#856404',
        padding: '10px'
      }));
      return;
    }

    if (selectedResults.length > 5) {
      comparisonResultsPanel.add(ui.Label('⚠️ Maximum 5 results can be compared at once.', {
        color: '#856404',
        padding: '10px'
      }));
      return;
    }

    comparisonResultsPanel.add(ui.Label('📊 Comparison Results', {
      fontWeight: 'bold',
      fontSize: '18px',
      margin: '10px 0 15px 0',
      color: '#004085'
    }));

    // Info panel
    var infoPanel = ui.Panel({
      style: {
        padding: '10px',
        borderRadius: '5px',
        margin: '0 0 15px 0',
        backgroundColor: '#e9ecef'
      }
    });
    comparisonResultsPanel.add(infoPanel);

    infoPanel.add(ui.Label('Selected Analyses:', {
      fontWeight: 'bold',
      margin: '0 0 10px 0',
      color: '#343a40'
    }));

    selectedResults.forEach(function(result, index) {
      var color = getColorForIndex(index);
      var labelText = '• ' + (result.parameter ? result.parameter.split(' - ')[0] : result.type) +
                        ' (' + result.areaName + ' - ' + result.type + ')';
      infoPanel.add(ui.Label(labelText, {
        color: color,
        fontSize: '13px',
        margin: '2px 0'
      }));
    });

    // Create main comparison chart
    createCombinedComparisonChart(selectedResults);

    // Add FFT Analysis Section
    var fftSection = ui.Panel({
      style: {
        margin: '20px 0',
        padding: '15px',
        backgroundColor: '#f0f8ff',
        borderRadius: '8px',
        border: '1px solid #b8daff'
      }
    });

    fftSection.add(ui.Label({
      value: '🌊 Frequency Analysis (FFT)',
      style: { fontWeight: 'bold', fontSize: '18px', margin: '0 0 15px 0', color: '#004085' }
    }));

    // Perform FFT analysis for any result with a valid time series
    selectedResults.forEach(function(result) {
      if (result.timeSeries && Array.isArray(result.timeSeries)) {
        var dates = result.timeSeries.map(function(d) { return d[0]; });
        var values = result.timeSeries.map(function(d) { return d[1]; });

        // Add feedback if there are not enough data points
        if (values.length > 10) { // Need sufficient data for FFT
          var name = result.parameter.split(' - ')[0] + ' (' + result.areaName + ' - ' + result.type + ')';
          createFFTAnalysisPanel(values, dates, name, fftSection);
        } else {
          fftSection.add(ui.Label('⚠️ Not enough data points (' + values.length +
            ') for FFT analysis of "' + result.parameter.split(' - ')[0] + ' (' + result.areaName + ')". Analysis requires > 10 points.', {
            padding: '10px',
            margin: '5px 0',
            backgroundColor: '#fff3cd',
            color: '#856404'
          }));
        }
      }
    });

    comparisonResultsPanel.add(fftSection);

    // Add Cross-Correlation Section if multiple results with time series are selected
    var timeSeriesResults = selectedResults.filter(function(r) {
      return r.timeSeries && Array.isArray(r.timeSeries);
    });

    if (timeSeriesResults.length >= 2) {
      var xcorrSection = ui.Panel({
        style: {
          margin: '20px 0', padding: '15px', backgroundColor: '#fff5f5',
          borderRadius: '8px', border: '1px solid #f5c6cb'
        }
      });
      xcorrSection.add(ui.Label({
        value: '📈 Cross-Correlation Analysis',
        style: { fontWeight: 'bold', fontSize: '18px', margin: '0 0 15px 0', color: '#721c24' }
      }));
      var corrControlPanel = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { margin: '10px 0' } });

      var getLabel = function(r) { return r.parameter.split(' - ')[0] + ' (' + r.areaName + ' - ' + r.type + ')'; };
      
      var param1Select = ui.Select({
        items: timeSeriesResults.map(getLabel),
        placeholder: 'Select first parameter', style: { width: '200px', margin: '0 10px 0 0' }
      });
      var param2Select = ui.Select({
        items: timeSeriesResults.map(getLabel),
        placeholder: 'Select second parameter', style: { width: '200px', margin: '0 10px 0 0' }
      });

      var correlateButton = ui.Button({
        label: 'Calculate Correlation',
        onClick: function() {
          var idx1 = timeSeriesResults.findIndex(function(r) { return getLabel(r) === param1Select.getValue(); });
          var idx2 = timeSeriesResults.findIndex(function(r) { return getLabel(r) === param2Select.getValue(); });

          if (idx1 >= 0 && idx2 >= 0 && idx1 !== idx2) {
            while (xcorrSection.widgets().length() > 3) {
              xcorrSection.remove(xcorrSection.widgets().get(3));
            }
            createCrossCorrelationPanel(timeSeriesResults[idx1], timeSeriesResults[idx2], xcorrSection);
          } else {
            print('⚠️ Please select two different parameters to correlate');
          }
        },
        style: { backgroundColor: '#dc3545', color: 'white', border: 'none', padding: '8px 16px' }
      });

      corrControlPanel.add(param1Select);
      corrControlPanel.add(param2Select);
      corrControlPanel.add(correlateButton);
      xcorrSection.add(corrControlPanel);
      xcorrSection.add(ui.Label('Select two parameters above to analyze their correlation', {
        fontSize: '12px', color: '#6c757d', fontStyle: 'italic'
      }));
      comparisonResultsPanel.add(xcorrSection);
    }

    // Show geometries button
    if (selectedResults.length > 0) {
      var showGeometriesButton = ui.Button({
        label: '🗺️ Show Geometries on Map',
        onClick: function() { visualizeComparisonGeometries(selectedResults); },
        style: {
          padding: '8px 16px',
          margin: '15px 0 5px 0',
          backgroundColor: '#17a2b8',
          color: 'white',
          border: 'none',
          borderRadius: '4px'
        }
      });
      comparisonResultsPanel.add(showGeometriesButton);
    }
  } catch (e) {
    print('❌ Error in generateAdvancedComparisonEnhanced: ' + e.toString());
    comparisonResultsPanel.add(ui.Label('❌ Error creating comparison: ' + e.toString(), {
      color: '#721c24',
      padding: '10px'
    }));
  }
}

// ===== END: INTEGRATED ANALYSIS FUNCTIONS =====


// --- EVENT HANDLERS ---
parameterSelect.onChange(function(selectedParam) {
  try {
    var isTrueColor = selectedParam.indexOf('True Color') > -1;
    var isTemp = selectedParam.indexOf('Temperature') > -1;
    var isSe2WaQ = selectedParam.indexOf('Se2WaQ') > -1;

    modeSelect.setDisabled(isTrueColor);
    paramWarningLabel.setValue('');

    if (isTemp) {
      paramWarningLabel.setValue('⚠️ Η θερμοκρασία είναι διαθέσιμη μόνο από Landsat 8/9');
      dataSourceSelect.setDisabled(true);
      dataSourceSelect.setValue('L2A - Surface Reflectance (Προεπιλογή)', false);
    } else {
      dataSourceSelect.setDisabled(false);

      if (isTrueColor) {
        modeSelect.setValue('Ανάλυση Περιοχής (ROI)', true);
        paramWarningLabel.setValue('Η ανάλυση Transect δεν είναι διαθέσιμη για την προβολή Πραγματικού Χρώματος.');
      }
      if (isSe2WaQ) {
         paramWarningLabel.setValue('💡 Τα μοντέλα Se2WaQ μπορεί να έχουν διαφορετική ακρίβεια με L1C δεδομένα.');
      }
    }

    if (globalDateList && globalDateList.length > 0) {
      var dateSlider = sliderPanel.widgets().get(1);
      if (dateSlider) {
          var currentIndex = dateSlider.getValue();
          showImageForDate(globalDateList[Math.round(currentIndex)]);
      }
    }
  } catch(e) {
    print('❌ Error in parameterSelect.onChange: ' + e.toString());
  }
});

dataSourceSelect.onChange(function(value) {
  try {
    var isL1C = value.indexOf('L1C') > -1;
    dataSourceInfoLabel.setValue(isL1C ?
      'ℹ️ L1C: Ακατέργαστα δεδομένα με ατμοσφαιρικές επιδράσεις' :
      'ℹ️ L2A: Ατμοσφαιρικά διορθωμένα δεδομένα'
    );

    if (drawingTools.layers().length() > 0 && drawingTools.layers().get(0).getEeObject()) {
      loadData();
    }
  } catch(e) {
    print('❌ Error in dataSourceSelect.onChange: ' + e.toString());
  }
});


// --- COLOR PALETTE HELPER FUNCTIONS ---
function generateSmoothPalette(hexPalette, steps) {
    function hexToRgb(hex) {
        var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)] : null;
    }

    function rgbToHex(rgb) {
        return "#" + ((1 << 24) + (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]).toString(16).slice(1).toUpperCase();
    }

    function interpolateColor(color1, color2, factor) {
        var result = color1.slice();
        for (var i = 0; i < 3; i++) {
            result[i] = Math.round(result[i] + factor * (color2[i] - result[i]));
        }
        return result;
    }

    var rgbPalette = hexPalette.map(hexToRgb);
    var smoothPalette = [];
    var n = rgbPalette.length - 1;
    if (n < 0) return [];

    for (var i = 0; i < steps; i++) {
        var p = i / (steps - 1);
        var segment = Math.floor(p * n);
        if (segment >= n) { segment = n - 1; }

        var factor = (p * n) - segment;
        var color1 = rgbPalette[segment];
        var color2 = rgbPalette[segment + 1];

        var interpolatedRgb = interpolateColor(color1, color2, factor);
        smoothPalette.push(rgbToHex(interpolatedRgb));
    }
    return smoothPalette;
}

// --- MAIN ANALYSIS FUNCTIONS ---
var showImageForDate = function() {};

function loadData() {
  try {
    globalGeometry = drawingTools.layers().get(0).getEeObject();
    var startDate = ee.Date(startDateBox.getValue());
    var endDate = ee.Date(endDateBox.getValue());
    var mode = modeSelect.getValue();
    var parameter = parameterSelect.getValue();

    if (!globalGeometry) {
      print('❌ Σφάλμα: Παρακαλώ σχεδιάστε πρώτα ' + (mode === 'Ανάλυση Περιοχής (ROI)' ? 'μια περιοχή' : 'μια γραμμή') + '.');
      return;
    }

    if (mode === 'Ανάλυση Υψομέτρου Λίμνης') {
      runLakeHeightAnalysis(globalGeometry, startDateBox.getValue(), endDateBox.getValue());
      return;
    }

    print('🔄 Αναζήτηση διαθέσιμων εικόνων...');
    sliderPanel.clear();
    sliderPanel.add(ui.Label('Φόρτωση...', {}));

    var bounds = (mode === 'Ανάλυση Περιοχής (ROI)' || mode === 'Ανάλυση Γραμμής (Transect)') ? globalGeometry : globalGeometry.buffer(1000);

    if (parameter.indexOf('Temperature') > -1) {
      var l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
        .filterBounds(bounds)
        .filterDate(startDate, endDate)
        .map(maskL8sr);
      var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        .filterBounds(bounds)
        .filterDate(startDate, endDate)
        .map(maskL8sr);
      globalImageCollection = ee.ImageCollection(l8.merge(l9)).sort('system:time_start');
    } else {
      var useL1C = dataSourceSelect.getValue().indexOf('L1C') > -1;
      var applyCloudMask = cloudMaskCheckbox.getValue();
      var scalingFactor = parseInt(scalingFactorBox.getValue()) || 10000;

      if (useL1C) {
        print('Loading Sentinel-2 L1C (Top of Atmosphere) data...');
        globalImageCollection = ee.ImageCollection("COPERNICUS/S2")
          .filterBounds(bounds)
          .filterDate(startDate, endDate)
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 35))
          .map(function(image) {
            var converted = convertToReflectance(image, scalingFactor);
            return applyCloudMask ? maskCloudsL1C(converted) : converted;
          })
          .sort('system:time_start');
      } else {
        print('Loading Sentinel-2 L2A (Surface Reflectance) data...');
        globalImageCollection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
          .filterBounds(bounds)
          .filterDate(startDate, endDate)
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 35))
          .map(function(image) {
            return applyCloudMask ? maskCloudsL2A(image) : image;
          })
          .sort('system:time_start');
      }
    }

    var timestamps = globalImageCollection.aggregate_array('system:time_start');

    timestamps.evaluate(function(tsList) {
      if (tsList && tsList.length > 0) {
        var dateList = tsList.map(function(timestamp) {
          var d = new Date(timestamp);
          var year = d.getFullYear();
          var month = ('0' + (d.getMonth() + 1)).slice(-2);
          var day = ('0' + d.getDate()).slice(-2);
          return year + '-' + month + '-' + day;
        });

        print('✅ Βρέθηκαν ' + dateList.length + ' εικόνες.');
        globalDateList = dateList;
        sliderPanel.clear();

        if (mode === 'Ανάλυση Περιοχής (ROI)') {
          setupRegionAnalysis(dateList);
        } else {
          setupTransectAnalysis(dateList);
        }

        // Show save button after successful data load
        saveResultButton.style().set('shown', true);
      } else {
        print('❌ Δεν βρέθηκαν εικόνες για αυτή την περίοδο.');
        sliderPanel.clear();
        sliderPanel.add(ui.Label('Δεν βρέθηκαν εικόνες.', { color: '#856404' }));
      }
    });
  } catch(e) {
    print('❌ Error in loadData: ' + e.toString());
  }
}

function setupRegionAnalysis(dateList) {
  try {
    var dateSlider = ui.Slider({
      min: 0,
      max: dateList.length - 1,
      value: 0,
      step: 1,
      style: {stretch: 'horizontal'},
      onChange: function(value) {
        var index = Math.round(value);
        showImageForDate(dateList[index]);
      }
    });

    var dateLabel = ui.Label('', {fontWeight: 'bold'});
    sliderPanel.add(ui.Label('Σύρετε για αλλαγή ημερομηνίας:', {}));
    sliderPanel.add(dateSlider);
    sliderPanel.add(dateLabel);

    showImageForDate = function(dateString) {
      try {
        dateLabel.setValue('Αναζήτηση για: ' + dateString);
        var selectedDate = ee.Date(dateString);
        var nearestImage = ee.Image(globalImageCollection.filter(ee.Filter.maxDifference({
          difference: 1000 * 60 * 60 * 24 * 3,
          leftField: 'system:time_start',
          rightValue: selectedDate.millis()
        })).sort('system:time_start').first());

        nearestImage.get('system:time_start').evaluate(function(val) {
          if (!val) {
            dateLabel.setValue('Δεν βρέθηκε κοντινή εικόνα για: ' + dateString);
            return;
          }

          var selectedParam = parameterSelect.getValue();
          var processedImage = processImage(nearestImage, selectedParam, false);
          var vizParams = getVizParams(selectedParam);
          var clippedImage = processedImage.clip(globalGeometry);
          var layer = ui.Map.Layer(clippedImage, vizParams, selectedParam.split(' - ')[0]);

          map.layers().set(1, layer);
          dateLabel.setValue('Εμφάνιση για: ' + ee.Date(val).format('YYYY-MM-dd').getInfo());
          updateLegend(selectedParam, vizParams);

          // Calculate and store statistics for comparison
          if (comparisonMode) {
            calculateROIStatistics(processedImage, selectedParam, dateString);
          }
        });
      } catch(e) {
        print('❌ Error in showImageForDate: ' + e.toString());
      }
    };

    showImageForDate(dateList[0]);
    parameterSelect.setValue(parameterSelect.getValue(), true);
  } catch(e) {
    print('❌ Error in setupRegionAnalysis: ' + e.toString());
  }
}

function setupTransectAnalysis(dateList) {
  try {
    sliderPanel.add(ui.Label('Επεξεργασία δεδομένων transect...', {fontWeight: 'bold'}));
    chartPanel.style().set('shown', true);
    mapPanel.style().set('width', '70%');

    if (transectLines.length === 0) {
      print('Error: No transect lines defined. Please add at least one transect line.');
      return;
    }

    var numPoints = parseInt(numPointsBox.getValue()) || 50;
    var selectedParam = parameterSelect.getValue();
    
    // Clear previous transect points layer
    var pointsList = [];
    
    // Process each transect line
    for (var lineIndex = 0; lineIndex < transectLines.length; lineIndex++) {
      var transect = transectLines[lineIndex];
      var line = transect.geometry;
      
      line.coordinates().evaluate(function(coords, lineProps) {
        if (!coords || coords.length < 2) {
          print('Error: Invalid line geometry for transect ' + lineProps.name);
          return;
        }

        var points = [];
        var totalLength = 0;
        var segmentLengths = [];
        
        // Calculate segment lengths
        for (var i = 0; i < coords.length - 1; i++) {
          var p1 = coords[i];
          var p2 = coords[i+1];
          var dx = p1[0] - p2[0];
          var dy = p1[1] - p2[1];
          var length = Math.sqrt(dx * dx + dy * dy);
          segmentLengths.push(length);
          totalLength += length;
        }

        var cumulativeLength = 0;
        var segmentIndex = 0;

        // Sample points along the line
        for (var j = 0; j < numPoints; j++) {
          var targetDist = (j / (numPoints - 1)) * totalLength;
          if (j === numPoints - 1) {
            targetDist = totalLength;
          }

          while (targetDist > cumulativeLength + segmentLengths[segmentIndex] && segmentIndex < segmentLengths.length - 1) {
            cumulativeLength += segmentLengths[segmentIndex];
            segmentIndex++;
          }

          var distIntoSegment = targetDist - cumulativeLength;
          var fractionAlongSegment = 0;
          if (segmentLengths[segmentIndex] > 0) {
            fractionAlongSegment = distIntoSegment / segmentLengths[segmentIndex];
          }

          var startPoint = coords[segmentIndex];
          var endPoint = coords[segmentIndex + 1];

          var x = startPoint[0] + (endPoint[0] - startPoint[0]) * fractionAlongSegment;
          var y = startPoint[1] + (endPoint[1] - startPoint[1]) * fractionAlongSegment;

          // Add line ID and color to point properties
          points.push(ee.Feature(
            ee.Geometry.Point([x, y]), 
            { 
              index: j,
              lineId: lineProps.id,
              lineName: lineProps.name,
              lineColor: lineProps.color,
              distance: targetDist
            }
          ));
        }
        
        // Add points to the main list
        pointsList = pointsList.concat(points);
        
        // If this is the last line, process all points
        if (lineIndex === transectLines.length - 1) {
          var pointsFC = ee.FeatureCollection(pointsList);
          
          // Update the map with all points
          var pointsLayer = ui.Map.Layer(pointsFC, {
            pointSize: 5,
            color: 'color',
            opacity: 0.7
          }, 'Transect Points');
          
          map.layers().set(2, pointsLayer);
          processTransectData(pointsFC, numPoints, selectedParam);
        }
      }.bind(this, transect)); // Pass transect properties to the callback
    }
  } catch(e) {
    currentAnalysisData = null;
    saveResultButton.setDisabled(true);
    saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
    print('❌ Error in setupTransectAnalysis: ' + e.toString());
  }
}

function processTransectData(pointsFC, numPoints, selectedParam) {
  try {
    // Group points by line ID for processing
    var values = globalImageCollection.map(function(image) {
      var date = ee.Date(image.get('system:time_start'));
      var unmaskedImage = image.unmask(0);

      var processedImage = processImage(unmaskedImage, selectedParam, false);
      var bandName = processedImage.bandNames().get(0);

      var waterMask;
      if (selectedParam.indexOf('Temperature') > -1) {
        waterMask = unmaskedImage.select('QA_PIXEL').bitwiseAnd(1 << 7).gt(0).rename('water');
      } else {
        waterMask = safeNormalizedDifference(unmaskedImage, 'B3', 'B8').gt(0).rename('water');
      }

      var combinedImage = processedImage.addBands(waterMask);

      // Sample values for all points
      var sampledData = combinedImage.reduceRegions({
        collection: pointsFC,
        reducer: ee.Reducer.first(),
        scale: 30,
        tileScale: 4
      });

      // Group values by line ID
      var groupedData = sampledData.aggregate_array(
        ee.Feature(null, {
          date: date.format('YYYY-MM-dd'),
          values: ee.Dictionary({
            values: ee.List([ee.Feature(sampledData.first()).get(bandName)]),
            lineId: ee.List([ee.Feature(sampledData.first()).get('lineId')]),
            lineName: ee.List([ee.Feature(sampledData.first()).get('lineName')]),
            lineColor: ee.List([ee.Feature(sampledData.first()).get('lineColor')]),
            is_water: ee.List([ee.Feature(sampledData.first()).get('water')])
          })
        })
      );

      // Combine features with the same date
      var combined = ee.FeatureCollection(groupedData).aggregate_histogram('date')
        .map(function(date, features) {
          var featureList = ee.List(features);
          var first = ee.Feature(featureList.get(0));
          
          // Combine all values
          var combinedValues = featureList.iterate(function(feature, acc) {
            return ee.Dictionary(acc).combine(ee.Feature(feature).get('values'));
          }, {});
          
          return ee.Feature(null, {
            date: date,
            values: combinedValues.get('values'),
            lineIds: combinedValues.get('lineId'),
            lineNames: combinedValues.get('lineName'),
            lineColors: combinedValues.get('lineColor'),
            is_water: combinedValues.get('is_water')
          });
        });

      return ee.Feature(combined.first());
    });

    values.evaluate(function(result) {
      if (!result) {
        sliderPanel.clear();
        sliderPanel.add(ui.Label('Σφάλμα: Δεν ήταν δυνατή η ανάλυση των δεδομένων.', { color: '#721c24' }));
        currentAnalysisData = null;
        saveResultButton.setDisabled(true);
        saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
        return;
      }

      var features = result.features || result;
      if (!Array.isArray(features) || features.length === 0) {
        sliderPanel.clear();
        sliderPanel.add(ui.Label('Σφάλμα: Δεν βρέθηκαν δεδομένα.', { color: '#721c24' }));
        currentAnalysisData = null;
        saveResultButton.setDisabled(true);
        saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
        return;
      }

      var data = [];
      var dates = [];
      var isWaterData = [];

      for (var i = 0; i < features.length; i++) {
        var feature = features[i];
        if (feature && feature.properties && feature.properties.values) {
          dates.push(feature.properties.date);
          data.push(feature.properties.values);
          isWaterData.push(feature.properties.is_water);
        }
      }

      if (data.length === 0) {
        sliderPanel.clear();
        sliderPanel.add(ui.Label('Δεν βρέθηκαν έγκυρα δεδομένα.', { color: '#856404' }));
        currentAnalysisData = null;
        saveResultButton.setDisabled(true);
        saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
        return;
      }

      // Safely get properties with fallbacks for Earth Engine compatibility
      var firstFeature = features[0] && features[0].properties ? features[0].properties : {};
      var lineIds = firstFeature.lineIds || [];
      var lineNames = firstFeature.lineNames || [];
      var lineColors = firstFeature.lineColors || [];
      
      // Map transect lines to a compatible format
      var geometries = [];
      for (var i = 0; i < transectLines.length; i++) {
        var line = transectLines[i];
        geometries.push({
          id: line.id,
          name: line.name,
          color: line.color,
          geometry: line.geometry
        });
      }
      
      currentAnalysisData = {
        type: 'transect',
        parameter: selectedParam,
        data: data,
        dates: dates,
        isWaterData: isWaterData,
        lineIds: lineIds,
        lineNames: lineNames,
        lineColors: lineColors,
        geometries: geometries
      };
      saveResultButton.setDisabled(false);
      saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
      createTransectHeatmap(data, dates, isWaterData, selectedParam);

      sliderPanel.clear();
      sliderPanel.add(ui.Label('Ανάλυση transect ολοκληρώθηκε!', {fontWeight: 'bold', color: '#155724'}));

      var updateButton = ui.Button({
        label: 'Ενημέρωση γραφήματος',
        onClick: function() {
          setupTransectAnalysis(globalDateList);
        },
        style: {
          stretch: 'horizontal',
          backgroundColor: '#e9ecef',
          color: '#212529',
          border: '1px solid #ced4da'
        }
      });
      sliderPanel.add(updateButton);
    });
  } catch(e) {
    print('❌ Error in processTransectData: ' + e.toString());
  }
}

function createTransectHeatmap(data, dates, isWaterData, parameter) {
  try {
    if (!data || data.length === 0 || !data[0] || data[0].length === 0) {
      chartPanel.clear();
      chartPanel.add(ui.Label('Σφάλμα: Δεν βρέθηκαν έγκυρα δεδομένα για τη δημιουργία γραφήματος transect.', { color: '#721c24' }));
      return;
    }

    chartPanel.clear();
    chartPanel.style().set('backgroundColor', '#f8f9fa');
    chartPanel.add(ui.Label({
      value: 'Χωροχρονική Ανάλυση: ' + parameter.split(' - ')[0],
      style: { fontWeight: 'bold', fontSize: '16px', margin: '0 0 10px 0' }
    }));

    var vizParams = getVizParams(parameter);
    var basePalette = vizParams.basePalette || vizParams.palette;
    var min = vizParams.min;
    var max = vizParams.max;
    var plausibleMax = 50;

    var allValues = [];
    data.forEach(function(row, i) {
      row.forEach(function(val, j) {
        if (isWaterData[i][j] && val !== null && !isNaN(val) && val < plausibleMax) {
          allValues.push(val);
        }
      });
    });

    var minVal = allValues.length > 0 ? Math.min.apply(null, allValues) : min;
    var maxVal = allValues.length > 0 ? Math.max.apply(null, allValues) : max;

    var chartData = [];
    chartData.push(['Ημερομηνία', 'Θέση στη Γραμμή', {'role': 'style'}, {'role': 'tooltip'}]);
    var parameterName = parameter.split(' - ')[0];

    for (var dateIdx = 0; dateIdx < dates.length; dateIdx++) {
      for (var pointIdx = 0; pointIdx < data[dateIdx].length; pointIdx++) {
        var value = data[dateIdx][pointIdx];
        var isWater = isWaterData[dateIdx][pointIdx];
        var color, styleString, tooltipString;

        if (isWater) {
          if (value !== null && !isNaN(value)) {
            var normalizedValue = Math.max(0, Math.min(1, (value - min) / (max - min)));
            var fullPalette = generateSmoothPalette(basePalette, 100);
            var colorIndex = Math.floor(normalizedValue * (fullPalette.length - 1));
            color = fullPalette[colorIndex];
            tooltipString = 'Ημ/νία: ' + dates[dateIdx] + '\n' + 'Σημείο: ' + pointIdx + ' (Water)\n' + parameterName + ': ' + value.toFixed(3);
          }
        } else {
          color = '#cccccc'; // Light grey for land
          tooltipString = 'Ημ/νία: ' + dates[dateIdx] + '\n' + 'Σημείο: ' + pointIdx + ' (Land)';
        }

        if (color) {
          styleString = 'point { size: 7; fill-color: ' + color + '; }';
          chartData.push([new Date(dates[dateIdx]), pointIdx, styleString, tooltipString]);
        }
      }
    }

    var scatterChart = ui.Chart(chartData, 'ScatterChart').setOptions({
        title: 'Τιμές κατά μήκος της γραμμής ανά ημερομηνία',
        hAxis: {
          title: 'Ημερομηνία',
          gridlines: { color: '#dee2e6' },
          format: 'yyyy-MM-dd',
          textStyle: { color: '#333333' },
          titleTextStyle: { color: '#333333' }
        },
        vAxis: {
          title: 'Θέση στη γραμμή (σημείο #)',
          minValue: 0,
          maxValue: data[0].length - 1,
          textStyle: { color: '#333333' },
          titleTextStyle: { color: '#333333' }
        },
        legend: 'none',
        backgroundColor: '#f8f9fa',
        chartArea: {width: '70%', height: '70%'},
        height: 400,
        pointSize: 7,
        explorer: {
          axis: 'horizontal',
          keepInBounds: true,
          maxZoomOut: 1,
        }
    });
    chartPanel.add(scatterChart);

    var averageValueData = [['Date', 'Average Value']];
    for (var i = 0; i < dates.length; i++) {
      var dailyValues = data[i];
      var dailyWaterFlags = isWaterData[i];
      var waterValues = [];
      for (var j = 0; j < dailyValues.length; j++) {
        if(dailyWaterFlags[j] && dailyValues[j] !== null && !isNaN(dailyValues[j]) && dailyValues[j] < plausibleMax) {
          waterValues.push(dailyValues[j]);
        }
      }

      if (waterValues.length > 0) {
        var sum = waterValues.reduce(function(a, b) { return a + b; }, 0);
        var average = sum / waterValues.length;
        averageValueData.push([new Date(dates[i]), average]);
      }
    }

    if (averageValueData.length > 1) {
      var timeSeriesChart = ui.Chart(averageValueData, 'LineChart').setOptions({
        title: 'Μέση Τιμή Γραμμής στο Χρόνο',
        vAxis: {
          title: 'Μέση Τιμή ('+ parameterName +')',
          textStyle: { color: '#333333' },
          titleTextStyle: { color: '#333333' }
        },
        hAxis: {
          title: 'Ημερομηνία',
          format: 'yyyy-MM-dd',
          textStyle: { color: '#333333' },
          titleTextStyle: { color: '#333333' }
        },
        height: 300,
        legend: 'none',
        colors: ['#007bff'],
        backgroundColor: '#f8f9fa',
        explorer: {
          axis: 'horizontal',
          keepInBounds: true,
          maxZoomOut: 1,
        }
      });
      chartPanel.add(timeSeriesChart);
    }

    var colorLegendPanel = ui.Panel({
      layout: ui.Panel.Layout.flow('horizontal'),
      style: {margin: '10px 0', padding: '0px 8px'}
    });
    var legendLabels = [];
    var legendColors = generateSmoothPalette(basePalette, 30);
    for (var k = 0; k < legendColors.length; k++) {
      legendLabels.push(ui.Label('', {
        backgroundColor: legendColors[k],
        padding: '8px 3px',
        margin: '0'
      }));
    }
    var colorBar = ui.Panel(legendLabels, ui.Panel.Layout.flow('horizontal'));
    colorLegendPanel.add(ui.Label(min.toFixed(2), {margin: '0 4px 0 0'}));
    colorLegendPanel.add(colorBar);
    colorLegendPanel.add(ui.Label(max.toFixed(2), {margin: '0 0 0 4px'}));
    chartPanel.add(ui.Label('Κλίμακα χρωμάτων (Νερό):', {fontWeight: 'bold'}));
    chartPanel.add(colorLegendPanel);

    var dateSelector = ui.Slider({
      min: 0,
      max: dates.length - 1,
      value: 0,
      step: 1,
      style: {stretch: 'horizontal'},
      onChange: function(index) {
        updateLineProfile(Math.round(index), dates, data, parameter);
      }
    });
    chartPanel.add(ui.Label('Επιλέξτε ημερομηνία για προφίλ γραμμής:', {fontWeight: 'bold', margin: '20px 0 5px 0'}));
    chartPanel.add(dateSelector);

    var lineProfilePanel = ui.Panel({style: {margin: '10px 0'}});
    chartPanel.add(lineProfilePanel);

    function updateLineProfile(dateIndex, dates, data, parameter) {
      try {
        lineProfilePanel.clear();
        var selectedDate = dates[dateIndex];
        var values = data[dateIndex];
        var lineData = [['Σημείο', parameter.split(' - ')[0]]];
        for (var l = 0; l < values.length; l++) {
          lineData.push([l, values[l]]);
        }

        var lineChart = ui.Chart(lineData, 'LineChart').setOptions({
            title: 'Προφίλ γραμμής για ' + selectedDate,
            explorer: {
              keepInBounds: true,
              maxZoomOut: 1,
            },
            hAxis: {
              title: 'Θέση στη γραμμή (σημείο #)',
              textStyle: { color: '#333333' },
              titleTextStyle: { color: '#333333' }
            },
            vAxis: {
              title: parameter.split(' - ')[0],
              viewWindow: { min: min, max: max },
              textStyle: { color: '#333333' },
              titleTextStyle: { color: '#333333' }
            },
            colors: ['#007bff'],
            pointSize: 5,
            lineWidth: 2,
            height: 300,
            backgroundColor: '#f8f9fa'
        });
        lineProfilePanel.add(lineChart);
      } catch(e) {
        print('❌ Error in updateLineProfile: ' + e.toString());
      }
    }

    updateLineProfile(0, dates, data, parameter);

    var statsPanel = ui.Panel({
      widgets: [
        ui.Label('Στατιστικά (μόνο για το νερό):', {fontWeight: 'bold'}),
        ui.Label('Ελάχιστο: ' + minVal.toFixed(3), {color: '#6c757d'}),
        ui.Label('Μέγιστο: ' + maxVal.toFixed(3), {color: '#6c757d'}),
        ui.Label('Εύρος: ' + (maxVal - minVal).toFixed(3), {color: '#6c757d'}),
        ui.Label('Μέσος όρος: ' + (allValues.length > 0 ? (allValues.reduce(function(a,b){return a+b;}, 0) / allValues.length).toFixed(3) : 'N/A'), {color: '#6c757d'})
      ],
      style: {margin: '10px 0'}
    });
    chartPanel.add(statsPanel);

    var exportButton = ui.Button({
      label: 'Εξαγωγή δεδομένων CSV',
      onClick: function() { exportTransectData(data, dates, parameter); },
      style: {
        backgroundColor: '#6f42c1',
        color: 'white',
        border: 'none',
        padding: '8px 16px'
      }
    });
    chartPanel.add(exportButton);
  } catch(e) {
    print('❌ Error in createTransectHeatmap: ' + e.toString());
  }
}

function exportTransectData(data, dates, parameter) {
  try {
    var header = 'Date';
    for (var i = 0; i < data[0].length; i++) {
      header += ',Point_' + (i + 1);
    }
    var csvContent = header + '\n';

    for (var j = 0; j < dates.length; j++) {
      csvContent += dates[j] + ',' + data[j].join(',') + '\n';
    }

    print('=== TRANSECT DATA EXPORT ===');
    print('Parameter: ' + parameter);
    print('Number of dates: ' + dates.length);
    print('Number of points: ' + (data[0] ? data[0].length : 0));
    print('Copy the data below to save as CSV:');
    print(csvContent);

    var features = [];
    for (var dateIndex = 0; dateIndex < dates.length; dateIndex++) {
      var properties = {date: dates[dateIndex]};
      for (var pointIndex = 0; pointIndex < data[dateIndex].length; pointIndex++) {
        properties['Point_' + (pointIndex + 1)] = data[dateIndex][pointIndex];
      }
      features.push(ee.Feature(null, properties));
    }

    var fc = ee.FeatureCollection(features);

    Export.table.toDrive({ collection: fc, description: 'transect_' + parameter.split(' - ')[0] + '_export', fileFormat: 'CSV' });
    print('✅ Export task created! Check the Tasks tab to start the export.');
  } catch(e) {
    print('❌ Error in exportTransectData: ' + e.toString());
  }
}

// --- PROCESSING FUNCTIONS ---

function maskL8sr(image) {
  var cloudShadowBitMask = (1 << 3);
  var cloudsBitMask = (1 << 5);
  var qa = image.select('QA_PIXEL');
  var mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0)
    .and(qa.bitwiseAnd(cloudsBitMask).eq(0));
  return image.updateMask(mask);
}

function maskCloudsL1C(image) {
  var qa = image.select('QA60');
  // For L1C, QA60 bit 10 is cloud, bit 11 is cirrus
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
    .and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  var aerosolMask = image.select('B1').lt(2000);
  return image.updateMask(mask.and(aerosolMask));
}

function maskCloudsL2A(image) {
  var scl = image.select('SCL');
  var mask = scl.eq(4).or(scl.eq(5)).or(scl.eq(6)).or(scl.eq(7)).or(scl.eq(11));
  return image.updateMask(mask);
}

function convertToReflectance(image, scalingFactor) {
  var factor = ee.Number(scalingFactor || 10000);
  var opticalBands = image.select(['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12']);
  var scaledBands = opticalBands.divide(factor);
  var otherBands = image.bandNames().removeAll(opticalBands.bandNames());
  var result = scaledBands.addBands(image.select(otherBands));
  return result.copyProperties(image, ['system:time_start']);
}

function safeNormalizedDifference(image, band1, band2) {
  var b1_safe = image.select(band1).add(0.0001);
  var b2_safe = image.select(band2).add(0.0001);
  var numerator = b1_safe.subtract(b2_safe);
  var denominator = b1_safe.add(b2_safe);
  return numerator.divide(denominator);
}

function processImage(image, parameter, applyMask) {
  var waterMask;
  var shouldApplyMask = (applyMask === false) ? false : true;

  if (parameter.indexOf('Temperature') > -1) {
    waterMask = image.select('QA_PIXEL').bitwiseAnd(1 << 7).gt(0);
  } else {
    if (parameter.indexOf('True Color') > -1) {
      waterMask = safeNormalizedDifference(image, 'B3', 'B8').gt(0);
    } else {
      waterMask = image.mask();
    }
  }

  if (parameter === 'True Color - Πραγματικό Χρώμα') {
    var useL1C = dataSourceSelect.getValue().indexOf('L1C') > -1;
    var vizBands = image.select(['B4', 'B3', 'B2']);
    if (!useL1C) {
      vizBands = vizBands.multiply(0.0001);
    }
    return vizBands.updateMask(waterMask);
  }

  switch(parameter) {
    case 'Water Surface Temperature - Θερμοκρασία Επιφάνειας (°C)':
      return calculateWST(image, waterMask, shouldApplyMask);
    case 'NDWI - Δείκτης Νερού':
      var ndwiImage = safeNormalizedDifference(image, 'B3', 'B8').rename('NDWI');
      return shouldApplyMask ? ndwiImage.updateMask(waterMask) : ndwiImage;
    default:
      var calculated = calculateByIndex(image, parameter);
      return applyMaskConditional(calculated, waterMask, shouldApplyMask);
  }
}

function calculateByIndex(image, parameter) {
  switch(parameter) {
    case 'GNIR - Λόγος Πράσινου/NIR': return calculateGNIR(image);
    case 'NDCI - Χλωροφύλλη': return calculateNDCI(image);
    case 'NDTI - Θολότητα': return calculateNDTI(image);
    case 'CDOM - Χρωματισμένη Οργανική Ύλη': return calculateCDOM(image);
    case 'TSM - Αιωρούμενα Στερεά': return calculateTSM(image);
    case 'Chl-a - Χλωροφύλλη-α (εκτίμηση)': return calculateChlorophyll(image);
    case 'FAI - Floating Algae Index': return calculateFAI(image);
    case 'Algae Bloom Detection - Ανίχνευση Ανθοφορίας': return detectAlgaeBloom(image);
    case 'Water Turbidity Classes - Κατηγορίες Θολότητας': return classifyTurbidity(image);
    case 'Anomaly Detection - Ανίχνευση Ανωμαλιών': return detectAnomalies(image);
    case 'Chl-a (Se2WaQ) - Χλωροφύλλη-α': return calculateChla_Se2WaQ(image);
    case 'Cya (Se2WaQ) - Κυανοβακτήρια': return calculateCya_Se2WaQ(image);
    case 'Turb (Se2WaQ) - Θολότητα (NTU)': return calculateTurb_Se2WaQ(image);
    case 'CDOM (Se2WaQ) - Οργανική Ύλη': return calculateCDOM_Se2WaQ(image);
    case 'DOC (Se2WaQ) - Διαλυμένος Άνθρακας': return calculateDOC_Se2WaQ(image);
    case 'Color (Se2WaQ) - Χρώμα Νερού': return calculateColor_Se2WaQ(image);
    default: return calculateNDCI(image);
  }
}

function getVizParams(parameter) {
  var defaultPalette = ['#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF0000'];
  var ndwiPalette = ['#8B4513', '#FFFF00', '#00FFFF', '#0000FF'];
  var tsmPalette = ['#0000FF', '#00FFFF', '#FFFF00', '#FF8000', '#FF0000'];
  var anomalyPalette = ['#00FF00', '#FF0000'];
  var tempPalette = ['#000080', '#0000FF', '#00FFFF', '#FFFF00', '#FF0000', '#800000'];
  var se2waq_base_palette = ['#496FF2', '#82D35F', '#FEFD05', '#FD0004', '#8E2026', '#D97CF5'];
  var paletteSteps = 100;
  var p;

  if (parameter === 'True Color - Πραγματικό Χρώμα') {
    return {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3};
  }

  switch(parameter) {
    case 'Water Surface Temperature - Θερμοκρασία Επιφάνειας (°C)': p = {min: 5, max: 35, basePalette: tempPalette}; break;
    case 'NDCI - Χλωροφύλλη': p = {min: -0.2, max: 0.6, basePalette: defaultPalette}; break;
    case 'NDTI - Θολότητα': p = {min: -0.2, max: 0.3, basePalette: tsmPalette}; break;
    case 'NDWI - Δείκτης Νερού': p = {min: -0.5, max: 0.8, basePalette: ndwiPalette}; break;
    case 'GNIR - Λόγος Πράσινου/NIR': p = {min: 1, max: 10, basePalette: defaultPalette}; break;
    case 'CDOM - Χρωματισμένη Οργανική Ύλη': p = {min: 0, max: 5, basePalette: defaultPalette}; break;
    case 'TSM - Αιωρούμενα Στερεά': p = {min: 0, max: 100, basePalette: tsmPalette}; break;
    case 'Chl-a - Χλωροφύλλη-α (εκτίμηση)': p = {min: 0, max: 30, basePalette: defaultPalette}; break;
    case 'FAI - Floating Algae Index': p = {min: -0.02, max: 0.05, basePalette: defaultPalette}; break;
    case 'Algae Bloom Detection - Ανίχνευση Ανθοφορίας': p = {min: 0, max: 3, basePalette: defaultPalette}; break;
    case 'Water Turbidity Classes - Κατηγορίες Θολότητας': p = {min: 1, max: 5, basePalette: tsmPalette}; break;
    case 'Anomaly Detection - Ανίχνευση Ανωμαλιών': p = {min: 0, max: 1, basePalette: anomalyPalette}; break;
    case 'Chl-a (Se2WaQ) - Χλωροφύλλη-α': p = {min: 0, max: 50, basePalette: se2waq_base_palette}; break;
    case 'Cya (Se2WaQ) - Κυανοβακτήρια': p = {min: 0, max: 100, basePalette: se2waq_base_palette}; break;
    case 'Turb (Se2WaQ) - Θολότητα (NTU)': p = {min: 0, max: 20, basePalette: se2waq_base_palette}; break;
    case 'CDOM (Se2WaQ) - Οργανική Ύλη': p = {min: 0, max: 5, basePalette: se2waq_base_palette}; break;
    case 'DOC (Se2WaQ) - Διαλυμένος Άνθρακας': p = {min: 0, max: 40, basePalette: se2waq_base_palette}; break;
    case 'Color (Se2WaQ) - Χρώμα Νερού': p = {min: 0, max: 50, basePalette: se2waq_base_palette}; break;
    default: p = {min: 0, max: 1, basePalette: ['blue', 'green', 'red']}; break;
  }

  p.palette = generateSmoothPalette(p.basePalette, paletteSteps);
  return p;
}

function applyMaskConditional(image, mask, apply) {
    return apply ? image.updateMask(mask) : image;
}

function calculateWST(image) {
  var thermalBand = image.select('ST_B10');
  return thermalBand.multiply(0.00341802).add(149.0).subtract(273.15).rename('WST');
}

function calculateNDCI(image) {
  return safeNormalizedDifference(image, 'B5', 'B4').rename('NDCI');
}

function calculateNDTI(image) {
  return safeNormalizedDifference(image, 'B4', 'B3').rename('NDTI');
}

function calculateGNIR(image) {
  var b8_safe = image.select('B8').add(0.0001);
  return image.select('B3').divide(b8_safe).rename('GNIR');
}

function calculateCDOM(image) {
  var b2_safe = image.select('B2').add(0.0001);
  return image.select('B3').divide(b2_safe).rename('CDOM');
}

function calculateTSM(image) {
  var useL1C = dataSourceSelect.getValue().indexOf('L1C') > -1;
  var b4_reflectance = useL1C ? image.select('B4') : image.select('B4').multiply(0.0001);
  return b4_reflectance.multiply(745.89).add(10.15).rename('TSM');
}

function calculateChlorophyll(image) {
  var b4_safe = image.select('B4').add(0.0001);
  var ratio = image.select('B5').divide(b4_safe);
  return ratio.pow(3.94).multiply(4.26).rename('Chl-a');
}

function calculateFAI(image) {
  var red = image.select('B4');
  var nir = image.select('B8');
  var swir = image.select('B11');
  var lambda_red = 665, lambda_nir = 842, lambda_swir = 1610;
  var baseline = red.add(swir.subtract(red).multiply((lambda_nir - lambda_red)/(lambda_swir - lambda_red)));
  return nir.subtract(baseline).rename('FAI');
}

function calculateChla_Se2WaQ(image) {
  var b1_safe = image.select('B1').add(0.0001);
  var ratio = image.select('B3').divide(b1_safe);
  return ee.Image(4.26).multiply(ratio.pow(3.94)).rename('Chla_Se2WaQ');
}

function calculateCya_Se2WaQ(image) {
  var b2_safe = image.select('B2').add(0.0001);
  var ratio = image.select('B3').multiply(image.select('B4')).divide(b2_safe);
  return ee.Image(115530.31).multiply(ratio.pow(2.38)).rename('Cya_Se2WaQ');
}

function calculateTurb_Se2WaQ(image) {
  var b1_safe = image.select('B1').add(0.0001);
  var ratio = image.select('B3').divide(b1_safe);
  return ee.Image(8.93).multiply(ratio).subtract(6.39).rename('Turb_Se2WaQ');
}

function calculateCDOM_Se2WaQ(image) {
  var b4_safe = image.select('B4').add(0.0001);
  var ratio = image.select('B3').divide(b4_safe);
  return ee.Image(537).multiply(ee.Image(-2.93).multiply(ratio).exp()).rename('CDOM_Se2WaQ');
}

function calculateDOC_Se2WaQ(image) {
  var b4_safe = image.select('B4').add(0.0001);
  var ratio = image.select('B3').divide(b4_safe);
  return ee.Image(432).multiply(ee.Image(-2.24).multiply(ratio).exp()).rename('DOC_Se2WaQ');
}

function calculateColor_Se2WaQ(image) {
  var b4_safe = image.select('B4').add(0.0001);
  var ratio = image.select('B3').divide(b4_safe);
  return ee.Image(25366).multiply(ee.Image(-4.53).multiply(ratio).exp()).rename('Color_Se2WaQ');
}

function updateLegend(parameter, vizParams) {
  legendPanel.clear();
  var legendTitle = ui.Label({
    value: 'Υπόμνημα: ' + parameter.split(' - ')[0],
    style: {fontWeight: 'bold', fontSize: '14px', margin: '0 0 4px 0'}
  });
  legendPanel.add(legendTitle);

  if (parameter.indexOf('True Color') > -1) {
    var description = ui.Label({
      value: 'Εμφάνιση φυσικών χρωμάτων (RGB).',
      style: {fontSize: '11px', margin: '4px 0 0 0', color: '#6c757d'}
    });
    legendPanel.add(description);
    return;
  }

  if (vizParams.basePalette) {
    var baseColors = vizParams.basePalette;
    var min = vizParams.min;
    var max = vizParams.max;
    var legendColors = generateSmoothPalette(baseColors, 30);
    var legendPanelLabels = ui.Panel({
      widgets: legendColors.map(function(color) {
        return ui.Label('', {
          backgroundColor: color,
          padding: '8px 3px',
          margin: '0'
        });
      }),
      layout: ui.Panel.Layout.flow('horizontal'),
      style: {}
    });
    var labels = ui.Panel({
      widgets: [
        ui.Label(min.toFixed(2), {margin: '0 4px 0 0'}),
        legendPanelLabels,
        ui.Label(max.toFixed(2), {margin: '0 0 0 4px'})
      ],
      layout: ui.Panel.Layout.flow('horizontal'),
      style: {}
    });
    legendPanel.add(labels);
  }

  var descriptions = {
    'Water Surface Temperature - Θερμοκρασία Επιφάνειας (°C)': 'Θερμοκρασία σε βαθμούς Κελσίου (°C).',
    'NDCI - Χλωροφύλλη': 'Υψηλές τιμές = περισσότερη χλωροφύλλη',
    'NDTI - Θολότητα': 'Υψηλές τιμές = μεγαλύτερη θολότητα',
    'NDWI - Δείκτης Νερού': 'Υψηλές τιμές = νερό, Χαμηλές = ξηρά',
    'GNIR - Λόγος Πράσινου/NIR': 'Υψηλές τιμές υποδηλώνουν νερό. Πολύ υψηλές τιμές μπορεί να σημαίνουν θολότητα.',
    'CDOM - Χρωματισμένη Οργανική Ύλη': 'Υψηλές τιμές = περισσότερη οργανική ύλη',
    'TSM - Αιωρούμενα Στερεά': 'mg/L - Υψηλές τιμές = περισσότερα στερεά',
    'Chl-a - Χλωροφύλλη-α (εκτίμηση)': 'μg/m³ - Υψηλές τιμές = ευτροφισμός',
    'FAI - Floating Algae Index': 'Θετικές τιμές = επιπλέοντα φύκη',
    'Algae Bloom Detection - Ανίχνευση Ανθοφορίας': '0: Καθαρό, 1: Χαμηλή, 2: Μέτρια, 3: Υψηλή ανθοφορία',
    'Water Turbidity Classes - Κατηγορίες Θολότητας': '1: Πολύ καθαρό, 2: Καθαρό, 3: Μέτρια, 4: Θολό, 5: Πολύ θολό',
    'Anomaly Detection - Ανίχνευση Ανωμαλιών': '0: Κανονικό, 1: Ανώμαλο/Ασυνήθιστο',
    'Chl-a (Se2WaQ) - Χλωροφύλλη-α': 'Unit: mg/m³',
    'Cya (Se2WaQ) - Κυανοβακτήρια': 'Unit: 10^3 cell/ml',
    'Turb (Se2WaQ) - Θολότητα (NTU)': 'Unit: NTU',
    'CDOM (Se2WaQ) - Οργανική Ύλη': 'Unit: mg/l',
    'DOC (Se2WaQ) - Διαλυμένος Άνθρακας': 'Unit: mg/l',
    'Color (Se2WaQ) - Χρώμα Νερού': 'Unit: mg.Pt/l'
  };

  var description = ui.Label({
    value: descriptions[parameter] || '',
    style: {fontSize: '11px', margin: '4px 0 0 0', color: '#6c757d'}
  });
  legendPanel.add(description);
}

function detectAlgaeBloom(image) {
  var ndci = calculateNDCI(image);
  var fai = calculateFAI(image);
  var chl = calculateChlorophyll(image);
  return ee.Image(0)
    .where(ndci.gt(0.1).and(chl.gt(5)), 1)
    .where(ndci.gt(0.3).and(chl.gt(15)), 2)
    .where(ndci.gt(0.5).and(chl.gt(25)).or(fai.gt(0.02)), 3)
    .rename('AlgaeBloom');
}

function classifyTurbidity(image) {
  var ndti = calculateNDTI(image);
  var tsm = calculateTSM(image);
  return ee.Image(1)
    .where(ndti.gt(-0.1).and(tsm.gt(10)), 2)
    .where(ndti.gt(0).and(tsm.gt(25)), 3)
    .where(ndti.gt(0.1).and(tsm.gt(50)), 4)
    .where(ndti.gt(0.2).and(tsm.gt(75)), 5)
    .rename('TurbidityClass');
}

function detectAnomalies(image) {
  var ndci = calculateNDCI(image);
  var ndti = calculateNDTI(image);
  var cdom = calculateCDOM(image);
  return ee.Image(0)
    .where(ndci.gt(0.7).or(ndci.lt(-0.3)), 1)
    .where(ndti.gt(0.4).or(ndti.lt(-0.3)), 1)
    .where(cdom.gt(8).or(cdom.lt(0.5)), 1)
    .rename('Anomaly');
}

// --- LAKE HEIGHT ANALYSIS FUNCTIONS ---

// Reference points data (date in YYYY-MM-DD format, elevation in meters)
var referencePoints = [
  {date: '2020-01-15', elevation: 95.2, label: 'Winter Reference'},
  {date: '2020-04-15', elevation: 96.8, label: 'Spring Reference'},
  {date: '2020-07-15', elevation: 94.5, label: 'Summer Reference'},
  {date: '2020-10-15', elevation: 95.9, label: 'Autumn Reference'},
  {date: '2021-01-15', elevation: 95.0, label: 'Winter Reference'}
];

function maskCloudsAndShadows_Lake(image) {
  var qa = image.select('QA60');
  var scl = image.select('SCL');
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0).and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  if (image.bandNames().contains('SCL')) {
    var sclMask = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
    mask = mask.and(sclMask);
  }
  return image.updateMask(mask);
}

function calculateNDWI_Lake(image) {
  return image.normalizedDifference(['B3', 'B8']).rename('ndwi');
}

function calculateMNDWI_Lake(image) {
  return image.normalizedDifference(['B3', 'B11']).rename('mndwi');
}

function calculateAWEInsh_Lake(image) {
  return image.expression('4 * (GREEN - SWIR1) - (0.25 * NIR + 2.75 * SWIR2)', {
    'GREEN': image.select('B3'), 'NIR': image.select('B8'),
    'SWIR1': image.select('B11'), 'SWIR2': image.select('B12')
  }).rename('awei');
}

function getWaterMask_Lake(image, method, threshold) {
  var proj = image.select('B4').projection();
  image = image.reproject({crs: proj, scale: 20});
  var ndwi = calculateNDWI_Lake(image);
  var mndwi = calculateMNDWI_Lake(image);
  var awei = calculateAWEInsh_Lake(image);
  var ndvi = image.normalizedDifference(['B8', 'B4']).rename('ndvi');
  image = image.addBands([ndwi, mndwi, awei, ndvi]);
  var waterMask;
  switch(method) {
    case 'NDWI Standard': waterMask = ndwi.gt(threshold); break;
    case 'MNDWI Enhanced': waterMask = mndwi.gt(threshold); break;
    case 'AWEInsh': waterMask = awei.gt(threshold * 1000); break;
    case 'Multi-Index Fusion': waterMask = ndwi.gt(threshold).or(mndwi.gt(threshold)).and(ndvi.lt(0.3)).and(awei.gt(0)); break;
    case 'Simple Threshold': waterMask = image.select('B8').lt(1000); break;
    default: waterMask = mndwi.gt(threshold - 0.1).and(ndvi.lt(0.3)).or(ndwi.gt(threshold).and(awei.gt(0)));
  }
  waterMask = waterMask.focal_min(1).focal_max(1).reproject({crs: proj, scale: 20});
  return image.addBands(waterMask.selfMask().rename('water'));
}

function calculateElevationData(withWater, dem, lakeRegion) {
  var elevationData = withWater.map(function(image) {
    var water = image.select('water');
    var waterBinary = water.gt(0).unmask(0);
    var exteriorShoreline = waterBinary.focal_max(1).subtract(waterBinary).gt(0);
    var interiorShoreline = waterBinary.subtract(waterBinary.focal_min(1)).gt(0);
    var exteriorElev = dem.updateMask(exteriorShoreline).reduceRegion({
      reducer: ee.Reducer.median(), geometry: lakeRegion, scale: 30, maxPixels: 1e9
    });
    var interiorElev = dem.updateMask(interiorShoreline).reduceRegion({
      reducer: ee.Reducer.median(), geometry: lakeRegion, scale: 30, maxPixels: 1e9
    });
    var area = water.multiply(ee.Image.pixelArea()).reduceRegion({
      reducer: ee.Reducer.sum(), geometry: lakeRegion, scale: 30, maxPixels: 1e9
    });
    var waterPixelCount = water.reduceRegion({
      reducer: ee.Reducer.count(), geometry: lakeRegion, scale: 30, maxPixels: 1e9
    });
    return ee.Feature(null, {
      'system:time_start': image.get('system:time_start'),
      'date': ee.Date(image.get('system:time_start')).format('YYYY-MM-dd'),
      'elevation': exteriorElev.get('DEM'),
      'elevation_interior': interiorElev.get('DEM'),
      'water_pixels': waterPixelCount.get('water'),
      'water_area_km2': ee.Number(area.get('water')).divide(1e6)
    });
  });

  var validData = elevationData
    .filter(ee.Filter.notNull(['elevation', 'elevation_interior']))
    .filter(ee.Filter.gt('water_pixels', 50));

  return validData;
}

function displayLakeHeightResults(dataCollection, dem, lakeRegion, imageCollection, showDebug) {
  try {
    dataCollection.size().evaluate(function(count) {
      if (count < 2) {
        chartPanel.clear();
        chartPanel.add(ui.Label('❌ Not enough valid measurements found!', {color: '#721c24', fontWeight: 'bold'}));
        currentAnalysisData = null;
        saveResultButton.setDisabled(true);
        saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
        return;
      }

      chartPanel.clear();
      chartPanel.add(ui.Label('✅ Analysis Complete! Found ' + count + ' valid measurements', {
        fontWeight: 'bold',
        color: '#155724'
      }));

      var linearFit = dataCollection.reduceColumns({
        reducer: ee.Reducer.linearFit(),
        selectors: ['water_area_km2', 'elevation']
      });

      linearFit.evaluate(function(fit) {
        if (!fit || fit.scale === undefined || fit.offset === undefined) {
          chartPanel.add(ui.Label('❌ Could not create Area-Height model.', {color: '#721c24'}));
          currentAnalysisData = null;
          saveResultButton.setDisabled(true);
          saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
          return;
        }

        var slope = ee.Number(fit.scale);
        var offset = ee.Number(fit.offset);

        var dataWithModel = dataCollection.map(function(feature) {
          var area = ee.Number(feature.get('water_area_km2'));
          var modelledElevation = area.multiply(slope).add(offset);
          return feature.set('modelled_elevation', modelledElevation);
        });

        // Check if reference points should be shown
        var showReferencePoints = referencePointsCheckbox && referencePointsCheckbox.getValue();
        
        // Create chart options
        var chartOptions = {
          title: 'Measured Lake Surface Elevation Over Time',
          hAxis: {
            title: 'Date',
            format: 'MMM yy',
            textStyle: { color: '#333333' },
            titleTextStyle: { color: '#333333' }
          },
          vAxis: {
            title: 'Elevation (m)',
            textStyle: { color: '#333333' },
            titleTextStyle: { color: '#333333' }
          },
          pointSize: 7,
          colors: ['#007bff', '#6f42c1', '#ff6b6b'],
          backgroundColor: '#f8f9fa',
          series: {
            0: {
              labelInLegend: 'Exterior Shoreline (Measured)',
              pointSize: 8,
              pointShape: 'diamond',
              visibleInLegend: true
            },
            1: {
              labelInLegend: 'Interior Shoreline (Measured)',
              pointSize: 8,
              pointShape: 'circle',
              visibleInLegend: true
            },
            2: {
              labelInLegend: 'Reference Points',
              pointSize: 10,
              pointShape: 'star',
              visibleInLegend: showReferencePoints
            }
          },
          trendlines: {
            0: {
              type: 'linear',
              color: '#dc3545',
              lineWidth: 2,
              opacity: 0.8,
              showR2: true,
              visibleInLegend: true
            }
          }
        };
        
        // Create the elevation chart with the main data series
        var elevChart = ui.Chart.feature.byFeature({
          features: dataWithModel,
          xProperty: 'system:time_start',
          yProperties: ['elevation', 'elevation_interior']
        }).setChartType('ScatterChart').setOptions(chartOptions);
        
        // Add reference points if enabled
        if (showReferencePoints && referencePoints) {
          referencePoints.forEach(function(point) {
            var pointDate = new Date(point.date);
            var pointData = {
              type: 'Point',
              coordinates: [0, 0],
              properties: {
                'system:time_start': pointDate.getTime(),
                'elevation': point.elevation,
                'label': point.label || 'Reference Point'
              }
            };
            
            var pointFeature = ee.Feature(pointData, {
              'system:time_start': pointDate.getTime(),
              'elevation': point.elevation,
              'label': point.label || 'Reference Point'
            });
            
            var pointChart = ui.Chart.feature.byFeature({
              features: [pointFeature],
              xProperty: 'system:time_start',
              yProperties: ['elevation']
            })
            .setChartType('ScatterChart')
            .setOptions({
              pointSize: 10,
              colors: ['#ff6b6b'],
              pointShape: 'star',
              dataOpacity: 1,
              series: {
                0: {
                  visibleInLegend: false
                }
              },
              hAxis: chartOptions.hAxis,
              vAxis: chartOptions.vAxis
            });
            
            // Merge the point chart with the main chart
            elevChart = ui.Chart([elevChart, pointChart]);
          });
        }

        var areaChart = ui.Chart.feature.byFeature({
          features: dataWithModel, xProperty: 'system:time_start', yProperties: ['water_area_km2']
        }).setChartType('LineChart').setOptions({
          title: 'Measured Lake Surface Area Over Time',
          hAxis: {
            title: 'Date',
            format: 'MMM yy',
            textStyle: { color: '#333333' },
            titleTextStyle: { color: '#333333' }
          },
          vAxis: {
            title: 'Area (km²)',
            textStyle: { color: '#333333' },
            titleTextStyle: { color: '#333333' }
          },
          lineWidth: 2,
          colors: ['#28a745'],
          curveType: 'function',
          backgroundColor: '#f8f9fa'
        });

        var modelChart = ui.Chart.feature.byFeature({
          features: dataWithModel, xProperty: 'system:time_start', yProperties: ['modelled_elevation']
        }).setChartType('LineChart').setOptions({
          title: 'Area-Derived Elevation Over Time',
          hAxis: {
            title: 'Date',
            format: 'MMM yy',
            textStyle: { color: '#333333' },
            titleTextStyle: { color: '#333333' }
          },
          vAxis: {
            title: 'Elevation (m)',
            textStyle: { color: '#333333' },
            titleTextStyle: { color: '#333333' }
          },
          lineWidth: 2.5,
          colors: ['#ffc107'],
          curveType: 'function',
          backgroundColor: '#f8f9fa'
        });

        // Add charts to panel
        chartPanel.add(elevChart);
        chartPanel.add(areaChart);
        chartPanel.add(modelChart);
        
        // Add event listener to update chart when reference points checkbox changes
        if (referencePointsCheckbox) {
          referencePointsCheckbox.onChange(function(checked) {
            // Re-run the analysis to update the chart with new settings
            runLakeHeightAnalysis(lakeRegion, startDateBox.getValue(), endDateBox.getValue());
          });
        }

        if (showDebug) {
          var statsPanel = ui.Panel({
            style: {
              backgroundColor: '#e9ecef',
              padding: '10px',
              margin: '10px 0'
            }
          });
          statsPanel.add(ui.Label('📊 Area-to-Elevation Model:', {fontWeight: 'bold'}));
          statsPanel.add(ui.Label('Slope: ' + fit.scale.toFixed(4), {color: '#6c757d'}));
          statsPanel.add(ui.Label('Offset: ' + fit.offset.toFixed(2), {color: '#6c757d'}));
          chartPanel.add(statsPanel);
        }

        map.centerObject(lakeRegion, 12);
        var latestImage = imageCollection.sort('system:time_start', false).first();
        map.addLayer(latestImage, {bands: ['B4', 'B3', 'B2'], min: 0, max: 3000}, 'Latest RGB', false);
        map.addLayer(latestImage.select('water').selfMask(), {palette: ['#007bff']}, 'Water Mask (Latest)');

        // Store data for comparison
        if (comparisonMode) {
          currentAnalysisData = {
            type: 'lakeHeight',
            elevationData: dataWithModel,
            areaData: dataWithModel,
            modelParams: fit,
            count: count
          };
          saveResultButton.setDisabled(false);
          saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
        }
      });
    });
  } catch(e) {
    currentAnalysisData = null;
    saveResultButton.setDisabled(true);
    saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
    print('❌ Error in displayLakeHeightResults: ' + e.toString());
  }
}

function executeHeightCalculation(imageCollection, dem, lakeRegion, method, threshold, showDebug) {
  var withWater = imageCollection.map(function(img) {
    return getWaterMask_Lake(img.select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12']), method, threshold);
  });
  var elevationData = calculateElevationData(withWater, dem, lakeRegion);
  displayLakeHeightResults(elevationData, dem, lakeRegion, withWater, showDebug);
}

function processWithComposites(s2, dem, lakeRegion, method, threshold, showDebug) {
  var dateRange = s2.reduceColumns(ee.Reducer.minMax(), ['system:time_start']);
  dateRange.evaluate(function(range) {
    if (!range || !range.min || !range.max) {
      chartPanel.clear();
      chartPanel.add(ui.Label('❌ No valid date range found.', {color: '#721c24'}));
      currentAnalysisData = null;
      saveResultButton.setDisabled(true);
      saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
      return;
    }
    var startYear = ee.Date(range.min).get('year').getInfo();
    var endYear = ee.Date(range.max).get('year').getInfo();
    var months = ee.List.sequence(1, 12);
    var years = ee.List.sequence(startYear, endYear);

    var monthlyComposites = years.map(function(year) {
      return months.map(function(month) {
        var filtered = s2.filter(ee.Filter.calendarRange(year, year, 'year'))
                           .filter(ee.Filter.calendarRange(month, month, 'month'));
        return ee.Algorithms.If(
          filtered.size().gt(0),
          filtered.median().set({'system:time_start': ee.Date.fromYMD(year, month, 15).millis(), 'has_bands': true}),
          ee.Image().set({'system:time_start': ee.Date.fromYMD(year, month, 15).millis(),'has_bands': false})
        );
      });
    }).flatten();
    var compositeCollection = ee.ImageCollection.fromImages(monthlyComposites)
                                          .filter(ee.Filter.eq('has_bands', true));

    compositeCollection.size().evaluate(function(size) {
      if (size === 0) {
        chartPanel.clear();
        chartPanel.add(ui.Label('❌ No valid monthly composites could be created.', {color: '#721c24'}));
        currentAnalysisData = null;
        saveResultButton.setDisabled(true);
        saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
        return;
      }
      if (showDebug) {
        chartPanel.add(ui.Label('🔄 Using ' + size + ' monthly composites for analysis.', {
          fontSize: '11px',
          color: '#6c757d'
        }));
      }
      executeHeightCalculation(compositeCollection, dem, lakeRegion, method, threshold, showDebug);
    });
  });
}

function runLakeHeightAnalysis(lakeRegion, startDate, endDate) {
  try {
    chartPanel.clear();
    chartPanel.add(ui.Label('🔄 Processing Lake Height Analysis... Please wait...', {
      fontWeight: 'bold',
      color: '#007bff'
    }));

    var cloudThreshold = lakeCloudSlider.getValue();
    var ndwiThreshold = lakeNdwiSlider.getValue();
    var method = lakeMethodSelect.getValue();
    var showDebug = lakeDebugCheckbox.getValue();
    var useCloudMasking = lakePreprocessCheckbox.getValue();
    var useComposite = lakeCompositeCheckbox.getValue();

    var dem = ee.ImageCollection('COPERNICUS/DEM/GLO30').select('DEM').mosaic();
    var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
      .filterDate(startDate, endDate).filterBounds(lakeRegion)
      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloudThreshold))
      .select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'QA60', 'SCL']);

    if (useCloudMasking) {
      s2 = s2.map(maskCloudsAndShadows_Lake);
    }

    s2.size().evaluate(function(collectionSize) {
      if (collectionSize === 0) {
        chartPanel.clear();
        chartPanel.add(ui.Label('❌ No Sentinel-2 images found!', {color: '#721c24', fontWeight: 'bold'}));
        chartPanel.add(ui.Label('Suggestions:\n• Extend your date range\n• Increase cloud coverage threshold\n• Check if Sentinel-2 covers this area',
          {whiteSpace: 'pre-wrap', fontSize: '12px', color: '#6c757d'}));
        currentAnalysisData = null;
        saveResultButton.setDisabled(true);
        saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
        return;
      }

      if (showDebug) {
        chartPanel.add(ui.Label('📊 Found ' + collectionSize + ' Sentinel-2 images', {
          fontSize: '11px',
          color: '#6c757d'
        }));
      }

      if (useComposite) {
        processWithComposites(s2, dem, lakeRegion, method, ndwiThreshold, showDebug);
      } else {
        executeHeightCalculation(s2, dem, lakeRegion, method, ndwiThreshold, showDebug);
      }
    });
  } catch(e) {
    print('❌ Error in runLakeHeightAnalysis: ' + e.toString());
  }
}

// --- COMPARISON AND HISTORY FUNCTIONS ---
function calculateROIStatistics(image, parameter, dateString) {
  try {
    var stats = image.reduceRegion({
      reducer: ee.Reducer.mean().combine({
        reducer2: ee.Reducer.stdDev(),
        sharedInputs: true
      }).combine({
        reducer2: ee.Reducer.min(),
        sharedInputs: true
      }).combine({
        reducer2: ee.Reducer.max(),
        sharedInputs: true
      }),
      geometry: globalGeometry,
      scale: 30,
      maxPixels: 1e9
    });

    stats.evaluate(function(result) {
      // Extract the proper band name for the parameter
      var bandName = Object.keys(result).find(function(key) {
        return key.indexOf('_mean') > -1;
      });

      var meanValue = null;
      if (bandName) {
        meanValue = result[bandName];
      } else {
        // Fallback to first available mean value
        for (var key in result) {
          if (key.endsWith('_mean')) {
            meanValue = result[key];
            break;
          }
        }
      }

      currentAnalysisData = {
        type: 'roi',
        parameter: parameter,
        stats: {
          mean: meanValue,
          stdDev: result[bandName ? bandName.replace('_mean', '_stdDev') : 'stdDev'],
          min: result[bandName ? bandName.replace('_mean', '_min') : 'min'],
          max: result[bandName ? bandName.replace('_mean', '_max') : 'max']
        },
        geometry: globalGeometry,
        date: dateString,
        timeSeries: [] // This should be populated with actual time series data
      };

      saveResultButton.setDisabled(false);
      saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
      print('✅ ROI statistics calculated for ' + dateString + ', mean value: ' + meanValue);
    });
  } catch(e) {
    currentAnalysisData = null;
    saveResultButton.setDisabled(true);
    saveResultButton.setLabel('💾 Αποθήκευση Αποτελέσματος');
    print('❌ Error in calculateROIStatistics: ' + e.toString());
  }
}

function collectROITimeSeries(callback) {
  try {
    var parameter = parameterSelect.getValue();
    var startDate = startDateBox.getValue();
    var endDate = endDateBox.getValue();

    print('📊 Collecting time series data for comparison...');

    var timeSeriesData = globalImageCollection.map(function(image) {
      var processedImage = processImage(image, parameter, true);
      var stats = processedImage.reduceRegion({
        reducer: ee.Reducer.mean(),
        geometry: globalGeometry,
        scale: 30,
        maxPixels: 1e9
      });

      return ee.Feature(null, {
        'system:time_start': image.get('system:time_start'),
        'date': ee.Date(image.get('system:time_start')).format('YYYY-MM-dd'),
        'mean_value': stats.values().get(0) // Get the first (and only) value
      });
    });
    
    timeSeriesData.evaluate(function(collection) {
      if (collection && collection.features) {
        var tsData = [];
        collection.features.forEach(function(feature) {
          if (feature.properties.mean_value !== null) {
            tsData.push([
              feature.properties.date,
              feature.properties.mean_value
            ]);
          }
        });
        
        if (callback) callback(tsData);
      }
    });
  } catch(e) {
    print('❌ Error in collectROITimeSeries: ' + e.toString());
    if (callback) callback([]);
  }
}

function deleteSavedResult(result) {
  try {
    print('⚠️ Διαγραφή αποτελέσματος με ID: ' + result.id);
    
    for (var areaName in savedResults) {
        var areaData = savedResults[areaName];
        var types = ['roi', 'transect', 'lakeHeight'];
        types.forEach(function(type) {
            var targetArray = areaData[type];
            var index = -1;
            for (var i = 0; i < targetArray.length; i++) {
                if (targetArray[i].id === result.id) {
                    index = i;
                    break;
                }
            }
            if (index > -1) {
                targetArray.splice(index, 1);
                print('✅ Το αποτέλεσμα διαγράφηκε από το "' + areaName + '".');
            }
        });
    }

    updateHistoryList();
    updateComparisonCheckboxes();

  } catch(e) {
    print('❌ Error in deleteSavedResult: ' + e.toString());
  }
}

function loadSavedResult(result) {
  try {
    // Switch to analysis tab
    showTab('analysis');
    
    // Set parameters
    startDateBox.setValue(result.dateRange.start);
    endDateBox.setValue(result.dateRange.end);
    if (result.parameter) {
      parameterSelect.setValue(result.parameter, false); // Do not trigger onchange
    }
    
    // Set mode
    modeSelect.setValue(result.mode, true); // Trigger onchange to update UI
    
    // Load geometry if available
    if (result.geometry) {
      // Clear existing drawings
      drawingTools.setShown(false);
      while (drawingTools.layers().length() > 0) {
        drawingTools.layers().remove(drawingTools.layers().get(0));
      }
      drawingTools.setShown(true);
      
      // Add saved geometry
      var geometryLayer = ui.Map.GeometryLayer({
        geometries: [result.geometry],
        name: 'loaded_geometry',
        color: '#28a745'
      });
      drawingTools.layers().add(geometryLayer);
      
      map.centerObject(ee.Geometry(result.geometry), 12);
      print('✅ Γεωμετρία φορτώθηκε από το αποθηκευμένο αποτέλεσμα');
    }
    
    print('✅ Οι παράμετροι φορτώθηκαν. Πατήστε "Εκτέλεση Ανάλυσης" για να επαναλάβετε.');
  } catch(e) {
    print('❌ Error in loadSavedResult: ' + e.toString());
  }
}

// Initialize UI
updateUIForMode('Ανάλυση Περιοχής (ROI)');
updateHistoryList();

print('🌊 Enhanced Water Quality Explorer loaded successfully!');
print('💡 Enable Comparison Mode (green) to save analyses for advanced multi-parameter comparison');