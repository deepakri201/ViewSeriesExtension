cmake_minimum_required(VERSION 3.13.4)

project(ViewSeriesExtension)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/ViewSeriesExtension")
set(EXTENSION_CATEGORY "Examples")
set(EXTENSION_CONTRIBUTORS "Deepa Krishnaswamy (BWH)")
set(EXTENSION_DESCRIPTION "This is an example of a simple extension to view a set of series when a user clicks on a study. The views layout contains the number of series that are in the study. The studies are populated by entries in the DICOM database.")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/ViewSeriesExtension.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/ViewSeriesExtension/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(ViewSeries)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
