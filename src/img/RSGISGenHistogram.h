/*
 *  RSGISGenHistogram.h
 *  RSGIS_LIB
 *
 *  Created by Pete Bunting on 16/07/2012.
 *  Copyright 2012 RSGISLib. All rights reserved.
 *  This file is part of RSGISLib.
 * 
 *  RSGISLib is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  RSGISLib is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with RSGISLib.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#ifndef RSGISGenHistogram_H
#define RSGISGenHistogram_H

#include <iostream>
#include <cmath>
#include <limits>

#include "img/RSGISCalcImage.h"
#include "img/RSGISCalcImageValue.h"
#include "img/RSGISImageBandException.h"
#include "img/RSGISImageCalcException.h"

// mark all exported classes/functions with DllExport to have
// them exported by Visual Studio
#undef DllExport
#ifdef _MSC_VER
    #ifdef rsgis_img_EXPORTS
        #define DllExport   __declspec( dllexport )
    #else
        #define DllExport   __declspec( dllimport )
    #endif
#else
    #define DllExport
#endif

namespace rsgis { namespace img {
	
    class DllExport RSGISGenHistogram
    {
    public:
        RSGISGenHistogram();
        void genHistogram(GDALDataset **datasets, unsigned int numDS, std::string outputFile, unsigned int imgBand, double imgMin, double imgMax, float maskValue, float binWidth);
        unsigned int* genGetHistogram(GDALDataset *dataset, unsigned int imgBand, double imgMin, double imgMax, float binWidth, unsigned int *nBins);
        void gen2DHistogram(GDALDataset **datasets, unsigned int numDS, unsigned int img1BandIdx, unsigned int img2BandIdx, double **histgramMatrix, unsigned int numBins, double *img1Bins, double *img2Bins, double img1Scale, double img2Scale, double img1Off, double img2Off, double *rSq);
        ~RSGISGenHistogram();
    };
	
	class DllExport RSGISGenHistogramCalcVal : public RSGISCalcImageValue
	{
	public:
		RSGISGenHistogramCalcVal(unsigned int *bins, float *binRanges, unsigned int band, unsigned int numBins, float maskValue, float binWidth);
		void calcImageValue(float *bandValues, int numBands);
		~RSGISGenHistogramCalcVal();
    protected:
        unsigned int *bins;
        float *binRanges;
        unsigned int band;
        float maskValue;
        float binWidth;
        unsigned int numBins;
	};
    
    class DllExport RSGISGenHistogramNoMaskCalcVal : public RSGISCalcImageValue
	{
	public:
		RSGISGenHistogramNoMaskCalcVal(unsigned int *bins, float *binRanges, unsigned int band, unsigned int numBins, float binWidth);
		void calcImageValue(float *bandValues, int numBands);
		~RSGISGenHistogramNoMaskCalcVal();
    protected:
        unsigned int *bins;
        float *binRanges;
        unsigned int band;
        float binWidth;
        unsigned int numBins;
	};
    
    
    class DllExport RSGISGen2DHistogramCalcVal : public RSGISCalcImageValue
    {
    public:
        RSGISGen2DHistogramCalcVal(unsigned int img1BandIdx, unsigned int img2BandIdx, double **histgramMatrix, unsigned int numBins, double *img1Bins, double *img2Bins, double img1Scale, double img2Scale, double img1Off, double img2Off);
        void calcImageValue(float *bandValues, int numBands);
        ~RSGISGen2DHistogramCalcVal();
    protected:
        unsigned int img1BandIdx;
        unsigned int img2BandIdx;
        double **histgramMatrix;
        unsigned int numBins;
        double *img1Bins;
        double *img2Bins;
        double img1Scale;
        double img2Scale;
        double img1Off;
        double img2Off;
    };
	
}}

#endif
