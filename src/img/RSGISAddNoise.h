/*
 *  RSGISAddNoise.h
 *  RSGIS_LIB
 *
 *  Created by Pete Bunting on 29/08/2008.
 *  Copyright 2008 RSGISLib.
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

#ifndef RSGISAddNoise_H
#define RSGISAddNoise_H

#include <iostream>
#include <cmath>
#include <stdlib.h>

#include "img/RSGISImageCalcException.h"
#include "img/RSGISCalcImageValue.h"

#include "math/RSGISRandomDistro.h"

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

namespace rsgis 
{
	namespace img
	{
		
		enum noiseType 
		{
			randomNoise,
			percentGaussianNoise
		};
		
		class DllExport RSGISAddRandomNoise : public RSGISCalcImageValue
			{
			public: 
				RSGISAddRandomNoise(int numberOutBands, float scale);
				void calcImageValue(float *bandValues, int numBands, double *output);
				~RSGISAddRandomNoise();
			protected:
				float scale;
			};
		
		class DllExport RSGISAddRandomGaussianNoisePercent : public RSGISCalcImageValue
		{
		public: 
			RSGISAddRandomGaussianNoisePercent(int numberOutBands, float scale);
			void calcImageValue(float *bandValues, int numBands, double *output);
			~RSGISAddRandomGaussianNoisePercent();
		protected:
			float scale;
            rsgis::math::RSGISRandDistroGaussian *gRand;
		};
	}
}

#endif

