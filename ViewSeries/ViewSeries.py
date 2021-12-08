# ViewSeries.py
#
# This is a simple example to get familar with programming in Slicer.
#
# The list of patients is extracted from the DICOM database and displayed. When
# the user clicks on a patient, the studies corresponding the patient are
# listed. Clicking on a study populates the viewer, where one view is created
# for each series. The corresponding data is displayed in each viewer.
#
# Notes:
#     https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#load-dicom-files-into-the-scene-from-a-folder
#     https://github.com/pieper/CompareVolumes/blob/master/CompareVolumes.py 
#     https://github.com/Slicer/Slicer/blob/master/Modules/Scripted/DICOMPlugins/DICOMScalarVolumePlugin.py
#     https://github.com/QIICR/QuantitativeReporting/blob/87852c8460ed54de70e8c838f16ddf62da539546/DICOMPlugins/DICOMSegmentationPlugin.py#L699
#     https://github.com/SlicerRt/SlicerRT/blob/master/DicomRtImportExport/DicomRtImportExportPlugin.py 
#     https://discourse.slicer.org/t/windows-slicer-util-loadvolume-loads-wrong-volume/641 
#     https://discourse.slicer.org/t/importing-dicom-files-in-my-own-module-c/12455/4 
#     https://www.tutorialspoint.com/pyqt/pyqt_qlistwidget.htm
#     https://stackoverflow.com/questions/22571706/how-to-list-all-items-from-qlistwidget
#     https://stackoverflow.com/questions/23835847/how-to-remove-item-from-qlistwidget/23836142
#
# To do:
#   Try with QListView instead of QListWidget?
#   Had to install Quantitative Reporting and SlicerRT extensions manually - how to load extensions automatically?
#
# Deepa Krishnaswamy
# December 2021
# Brigham and Women's Hospital
################################################################################

from slicer.util import VTKObservationMixin

# from __future__ import division
import os, json, xml.dom.minidom, string, glob, re, math
import vtk, qt, ctk, slicer
import logging
import CompareVolumes
from Editor import EditorWidget
from EditorLib.EditUtil import EditUtil
import SimpleITK as sitk
import sitkUtils
import datetime
from slicer.ScriptedLoadableModule import *

# from mpReviewPreprocessor import mpReviewPreprocessorLogic
#
# from qSlicerMultiVolumeExplorerModuleWidget import qSlicerMultiVolumeExplorerSimplifiedModuleWidget
# from qSlicerMultiVolumeExplorerModuleHelper import qSlicerMultiVolumeExplorerModuleHelper as MVHelper
#
# from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin
# from SlicerDevelopmentToolboxUtils.helpers import WatchBoxAttribute
# from SlicerDevelopmentToolboxUtils.widgets import TargetCreationWidget, XMLBasedInformationWatchBox
# from SlicerDevelopmentToolboxUtils.icons import Icons

from DICOMLib import DICOMPlugin

################################################################################

#
# ViewSeries
#

class ViewSeries(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "ViewSeries"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["Examples"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Deepa Krishnaswamy (BWH)"]  # TODO: replace with "Firstname Lastname (Organization)"
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """This is an example of a simple extension to view a set of series when a user clicks on a study.
                              The views layout contains the number of series that are in the study.
                              The studies are populated by entries in the DICOM database."""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
                                         and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1."""

    # # Add this test to the SelfTest module's list for discovery when the module
    # # is created.  Since this module may be discovered before SelfTests itself,
    # # create the list if it doesn't already exist.
    # try:
    #     slicer.selfTests
    # except AttributeError:
    #     slicer.selfTests = {}
    #
    # def runTest(self):
    #     return

    # Additional initialization step after application startup is complete
    # slicer.app.connect("startupCompleted()", registerSampleData)

#
# ViewSeriesWidget
#

class ViewSeriesWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False
    # added
    self.selectPatientName = ''
    self.selectStudyName = ''
    self.studyCollapsibleButton = None
    self.studyListWidget = None
    self.selectPatientNameIndex = None
    self.selectStudyNameIndex = None
    self.studyListWidgetNum = 0 # number of studies
    self.seriesListNum = 0 # number of series
    self.patientNames = None
    self.db = slicer.dicomDatabase
    self.patientList = None

  def selectPatient(self, item):

      """This is called when the user selects a patient name from the list.
         The corresponding study names are listed when a patient is selected.
      """

      print ('Patient ' + str(item.text()) + ' was clicked')
      self.selectPatientName = item.text()

      # Get the info from the slicer database
      # We need to find where the self.selectPatientName appears in the list of the patientNames
      patientList = list(self.db.patients())
      patientNames = []
      for patient in range(0,len(patientList)):
          studyList = self.db.studiesForPatient(patientList[patient])
          seriesList = self.db.seriesForStudy(studyList[0])
          fileList = self.db.filesForSeries(seriesList[0])
          patientNames.append(self.db.fileValue(fileList[0], "0010,0010"))
      self.patientNames = patientNames

      # Find which one it is in the list of patients
      index = patientNames.index(self.selectPatientName)
      patientNameClicked = patientNames[index]
      self.selectPatientNameIndex = index

      # Get the study names from the patient that was selected
      studyList = self.db.studiesForPatient(patientList[index])
      print ('studyList: ' + str(studyList)) # this is correct

      ### There must be a better way to do this! Fix later ###
      # First remove the previous studies from the list
      if not (self.studyListWidgetNum == 0): # if it's not equal to 0, remove items
          num_items = self.studyListWidget.count
          # get a list of the current items
          items = []
          for n in range(0,num_items):
              items.append(self.studyListWidget.item(n))
          # now remove these items from the list
          for item in items:
              self.studyListWidget.takeItem(self.studyListWidget.row(item))

      # Add the new study items in
      for study in studyList:
          self.studyListWidget.addItem(study)
      self.studyListWidgetNum = (self.studyListWidget).count
      print ('self.studyListWidgetNum: ' + str(self.studyListWidgetNum)) # this is correct, is 2

      # need to update the layout??

      # Select the study and then get the series and update the viewer.
      self.studyListWidget.itemClicked.connect(self.selectStudy)


  def selectStudy(self, item):

    """This is called when the user selects a study name from the list."""

    print ('Study ' + str(item.text()) + ' was clicked') # why is this printing out multiple times?
    self.selectStudyName = item.text()

    ### Get the index of the study that was clicked ###
    # Find which one it is in the list of studies

    # patientList = list(self.db.patients())
    index = self.patientNames.index(self.selectPatientName)
    # print ("index of the patient: " + str(index))

    # print ('selectPatientNameIndex: ' + str(self.selectPatientNameIndex))
    # studyNames = db.studiesForPatient(self.selectPatientNameIndex)
    # studyNames = db.studiesForPatient(index)
    # studyNames = self.db.studiesForPatient(patientList[index])
    studyNames = self.db.studiesForPatient(self.patientList[index])
    # print ('studyNames: ' + str(studyNames))

    index = studyNames.index(self.selectStudyName)
    studyNameClicked = studyNames[index]
    # Get the series names from the study that was selected
    seriesList = self.db.seriesForStudy(studyNames[index])
    print ('seriesList: ' + str(seriesList))
    self.seriesListNum = len(seriesList)
    print ('number of series: ' + str(self.seriesListNum))


    ### Get the data from each series as a node and store in self.volumeNodes
    # Should not use slicer.util.loadVolume to load a DICOM file, as we may have a 
    # series of DICOM files. Better to use he plugin below. 
    
    # for the scalar volumes 
    DICOMScalarVolumePlugin = slicer.modules.dicomPlugins['DICOMScalarVolumePlugin']()
    # for the SEG label volumes 
    DICOMSegmentationPlugin = slicer.modules.dicomPlugins['DICOMSegmentationPlugin']()
    # for RTSTRUCT 
    DicomRtImportExportPlugin = slicer.modules.dicomPlugins['DicomRtImportExportPlugin']()
    
    self.volumeNodes = [] 
    
    for n in range(0,self.seriesListNum):
        # Get the list of files 
        fileList = self.db.filesForSeries(seriesList[n]) # should be n not 0 
        print ('fileList: ' + str(fileList))
        
        # Check the modality, only load MR for now 
        modality = self.db.fileValue(fileList[0], "0008,0060")
        print ('modality: ' + str(modality))
        if (modality=="CT" or modality == "MR"):
            loadables = DICOMScalarVolumePlugin.examineFiles(fileList)
            volume = DICOMScalarVolumePlugin.load(loadables[0]) # why 0? 
            self.volumeNodes.append(volume)
        # elif (modality=="SEG"):
        #     loadables = DICOMSegmentationPlugin.examineFiles(fileList)
        #     volume = DICOMSegmentationPlugin.load(loadables[0]) # why 0? 
        #     self.volumeNodes.append(volume)
        # elif (modality=="RTSTRUCT"):
        #     loadables = DicomRtImportExportPlugin.examineForImport(fileList)
        #     volume = DicomRtImportExportPlugin.load(loadables[0])
        #     self.volumeNodes.append(volume)

        
        
        
    ### Create as many views as the number of studies ###
    self.cvLogic = CompareVolumes.CompareVolumesLogic()
    # The data for each volume is stored in self.volumeNodes 
    
    # It will automatically figure out the layout in number of rowsxcolumns
    self.cvLogic.viewerPerVolume(self.volumeNodes)
    # self.cvLogic.viewerPerVolume(self.volumeNodes,\
    #                              viewNames=self.sliceNames,\
    #                              orientation=self.currentOrientation)

    ### Populate each view ###



  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    This creates a list of the patient names from the DICOM database, which the user then must select.
    """

    # This adds the Reload & Test
    ScriptedLoadableModuleWidget.setup(self)

    ### See if I can get list of patients from slicer DICOM database ###
    self.db = slicer.dicomDatabase
    patientList = list(self.db.patients())
    self.patientList = patientList
    # Get all the patient names in the database
    # For some reason, not all are listed - probably doesn't do nested names
    patientNames = []
    for patient in range(0,len(patientList)):
        studyList = self.db.studiesForPatient(patientList[patient])
        seriesList = self.db.seriesForStudy(studyList[0])
        fileList = self.db.filesForSeries(seriesList[0])
        patientNames.append(self.db.fileValue(fileList[0], "0010,0010"))
    print ('patientNames: ' + str(patientNames))

    ####### Displaying the patient names ###########
    # Collapsible button
    patientCollapsibleButton = ctk.ctkCollapsibleButton()
    patientCollapsibleButton.text = "Patient names"
    self.layout.addWidget(patientCollapsibleButton)

    ### Try with QListWidget - works ###
    patientListWidget = qt.QListWidget()
    for patient in patientNames:
        patientListWidget.addItem(patient)

    # Layout within the patientcollapsible button
    patientLayout = qt.QFormLayout(patientCollapsibleButton)
    patientLayout.addWidget(patientListWidget)

    # check if a patient name is clicked
    patientListWidget.itemClicked.connect(self.selectPatient)

    ###### Creating a layout for the study names #####

    # Collapsible button
    studyCollapsibleButton = ctk.ctkCollapsibleButton()
    studyCollapsibleButton.text = "Study names"
    self.layout.addWidget(studyCollapsibleButton)
    self.studyCollapsibleButton = studyCollapsibleButton

    self.studyListWidget = qt.QListWidget()
    self.studyLayout = qt.QFormLayout(self.studyCollapsibleButton)
    self.studyLayout.addWidget(self.studyListWidget)

    # ### Try wtih QListView ###
    # sampleLayout = qt.QVBoxLayout()
    # listView = qt.QListView()
    # # listView.setSpacing(3)
    # # listView.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
    # listModel = qt.QStandardItemModel()
    # item = qt.QStandardItem("Item 1")
    # listModel.appendRow(item)
    # item = qt.QStandardItem("Item 2")
    # listModel.appendRow(item)
    # item = qt.QStandardItem("Item 3")
    # listModel.appendRow(item)
    # listView.setModel(listModel)
    # # listView.show()
    # sampleLayout.addWidget(listView)

#
# ViewSeriesLogic
#

# class ViewSeriesLogic(ScriptedLoadableModuleLogic):
#   """This class should implement all the actual
#   computation done by your module.  The interface
#   should be such that other python code can import
#   this class and make use of the functionality without
#   requiring an instance of the Widget.
#   Uses ScriptedLoadableModuleLogic base class, available at:
#   https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
#   """
#
#   def __init__(self):
#     """
#     Called when the logic class is instantiated. Can be used for initializing member variables.
#     """
#     ScriptedLoadableModuleLogic.__init__(self)
#
#   def setDefaultParameters(self, parameterNode):
#     """
#     Initialize parameter node with default settings.
#     """
#     if not parameterNode.GetParameter("Threshold"):
#       parameterNode.SetParameter("Threshold", "100.0")
#     if not parameterNode.GetParameter("Invert"):
#       parameterNode.SetParameter("Invert", "false")
#
#   def process(self, inputVolume, outputVolume, imageThreshold, invert=False, showResult=True):
#     """
#     Run the processing algorithm.
#     Can be used without GUI widget.
#     :param inputVolume: volume to be thresholded
#     :param outputVolume: thresholding result
#     :param imageThreshold: values above/below this threshold will be set to 0
#     :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
#     :param showResult: show output volume in slice viewers
#     """
#
#     if not inputVolume or not outputVolume:
#       raise ValueError("Input or output volume is invalid")
#
#     import time
#     startTime = time.time()
#     logging.info('Processing started')
#
#     # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
#     cliParams = {
#       'InputVolume': inputVolume.GetID(),
#       'OutputVolume': outputVolume.GetID(),
#       'ThresholdValue' : imageThreshold,
#       'ThresholdType' : 'Above' if invert else 'Below'
#       }
#     cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
#     # We don't need the CLI module node anymore, remove it to not clutter the scene with it
#     slicer.mrmlScene.RemoveNode(cliNode)
#
#     stopTime = time.time()
#     logging.info('Processing completed in {0:.2f} seconds'.format(stopTime-startTime))
#
# #
# # ViewSeriesTest
# #
