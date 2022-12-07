import traceback
import adsk.fusion
import adsk.core
import pathlib
import re

DEBUG = False


class LowPoly_Factry():
    def __init__(self) -> None:
        self.app: adsk.core.Application = adsk.core.Application.get()
        self.tmpMgr: adsk.fusion.TemporaryBRepManager = adsk.fusion.TemporaryBRepManager.get()


    def export_meshes(
        self,
        bodies: list,
        Tolerance: float,
        lengthRatio: float,
        path: str,
        isOneFile: bool) -> None:

        # *******

        basePath = pathlib.Path(path)
        baseDir = basePath.parent
        stem = re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', basePath.stem)
        suffix = basePath.suffix

        stlSourceList = [self._get_mesh_data(b, Tolerance, lengthRatio, b.name) for b in bodies]

        datas = []
        if isOneFile:
            expPath = baseDir / f'{stem}{suffix}'
            datas.append((str(expPath), '\n'.join(stlSourceList)))
        else:
            for body, source in zip(bodies, stlSourceList):
                bodyName = re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', body.name)
                expPath = baseDir / f'{stem}_{bodyName}{suffix}'
                datas.append((str(expPath), source))

        [self._write_file(p, s) for p, s in datas]


    def _write_file(
        self,
        path: str,
        txt: str) -> None:

        with open(path, mode='w') as f:
            f.write(txt)


    def _get_mesh_data(
        self,
        body: adsk.fusion.BRepBody,
        Tolerance: float,
        lengthRatio: float,
        name: str) -> str:

        meshCalc: adsk.fusion.TriangleMeshCalculator = body.meshManager.createMeshCalculator()
        meshCalc.surfaceTolerance = Tolerance
        traMesh: adsk.fusion.TriangleMesh = meshCalc.calculate()

        points = self._group_by_list(
            traMesh.nodeCoordinates,
            self._group_by_count(traMesh.nodeIndices, 3)
        )
        tmpNormals = self._group_by_list(
            traMesh.normalVectors,
            self._group_by_count(traMesh.nodeIndices, 3)
        )
        normals = [self._synthesize_vectors(vs) for vs in tmpNormals]

        return self._initStlSource(points, normals, lengthRatio, name)


    def _synthesize_vectors(
        self,
        vectors: list) -> adsk.core.Vector3D:

        v: adsk.core.Vector3D = vectors[0].copy()
        v.add(vectors[1])
        v.add(vectors[2])
        v.normalize()

        return v


    def _group_by_count(
        self,
        lst: list,
        count: int) -> list:

        return [lst[i: i+count] for i in range(0, len(lst), count)]


    def _group_by_list(
        self,
        lst: list,
        indexLst: list) -> list:

        res = []
        for idxs in indexLst:
            res.append(
                (
                    lst[idxs[0]],
                    lst[idxs[1]],
                    lst[idxs[2]],
                )
            )
        return res


    def _initStlSource(
        self,
        pointsSet: list,
        normals: list,
        lengthRatio: float,
        name: str = 'ASCII') -> str:

        stl = [f'solid {name}']
        for ps, v in zip(pointsSet, normals):
            stl.append(f'  facet normal {v.x} {v.y} {v.z}')
            stl.append(f'    outer loop')
            for p in ps:
                stl.append(f'      vertex   {p.x * lengthRatio} {p.y * lengthRatio} {p.z * lengthRatio}')
            stl.append(f'    endloop')
            stl.append(f'  endfacet')
        stl.append(f'endsolid')

        return '\n'.join(stl)


def dump(s):
    if not DEBUG:
        return

    adsk.core.Application.get().log(f'{s}')
    print(s)