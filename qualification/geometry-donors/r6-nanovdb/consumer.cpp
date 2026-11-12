// Original public-safe independent NanoVDB read-oriented sparse grid consumer.
#include <nanovdb/NanoVDB.h>
#include <nanovdb/tools/CreatePrimitives.h>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
int main() {
    constexpr double radius=8.0, voxel=1.0, half_width=3.0;
    auto handle=nanovdb::tools::createLevelSetSphere<float>(
         radius,nanovdb::Vec3d(0.0),voxel,half_width);
    auto* grid=handle.grid<float>();
    if(!grid) throw std::runtime_error("NO_GRID");
    if(reinterpret_cast<uintptr_t>(grid)%NANOVDB_DATA_ALIGNMENT!=0)
        throw std::runtime_error("BAD_GRID_ALIGNMENT");
    auto center=grid->tree().getValue(nanovdb::Coord(0,0,0));
    auto inside=grid->tree().getValue(nanovdb::Coord(7,0,0));
    auto outside=grid->tree().getValue(nanovdb::Coord(9,0,0));
    if(!std::isfinite(center)||!std::isfinite(inside)||!std::isfinite(outside))
        throw std::runtime_error("NONFINITE_VALUE");
    if(!(center<0 && inside<0 && outside>0))
        throw std::runtime_error("SDF_POLARITY_FAILURE");
    if(std::abs(inside+1.f)>0.15f||std::abs(outside-1.f)>0.15f)
        throw std::runtime_error("LEVEL_SET_QUANTIZATION_FAILURE");
    if(NANOVDB_MAJOR_VERSION_NUMBER!=32)
        throw std::runtime_error("SERIALIZED_GRID_ABI_MISMATCH");
    std::cout<<"NANOVDB_READ_ORACLE_PASS center="<<center
       <<" inside="<<inside<<" outside="<<outside
       <<" alignment="<<NANOVDB_DATA_ALIGNMENT
       <<" abi="<<NANOVDB_MAJOR_VERSION_NUMBER<<"."<<NANOVDB_MINOR_VERSION_NUMBER
       <<"\n";
    return 0;
}
