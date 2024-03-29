import traceback
import adsk.fusion
import adsk.core
import pathlib
import re
from itertools import chain

DEBUG = False


class LowPoly_Factry():
    def __init__(self) -> None:
        self.app: adsk.core.Application = adsk.core.Application.get()
        self.tmpMgr: adsk.fusion.TemporaryBRepManager = adsk.fusion.TemporaryBRepManager.get()
        self.cgColor = adsk.fusion.CustomGraphicsShowThroughColorEffect.create(
            adsk.core.Color.create(
                255, 0, 0, 255
            ),
            0.2
        )


    def preview_meshes(
        self,
        entities: list,
        tolerance: float,) -> int:

        bodies = self._get_target_bodies(entities)
        for body in bodies:
            body.opacity = 0.3

        root: adsk.fusion.Component = self.app.activeProduct.rootComponent
        cgGroup: adsk.fusion.CustomGraphicsGroup = root.customGraphicsGroups.add()

        count = 0
        for body in bodies:
            traMesh: adsk.fusion.TriangleMesh = self._get_triangleMesh(body, tolerance)
            count += self._init_cg_wires(traMesh, cgGroup)

        return count


    def _init_cg_wires(
        self,
        traMesh: adsk.fusion.TriangleMesh,
        cgGroup: adsk.fusion.CustomGraphicsGroup) -> int:

        pointSet = self._group_by_count(traMesh.nodeCoordinatesAsFloat, 3)
        nodeIndiceSet = self._group_by_count(traMesh.nodeIndices, 3)

        for i0, i1, i2 in nodeIndiceSet:
            lst = list(chain.from_iterable(
                [pointSet[i0], pointSet[i1], pointSet[i2], pointSet[i0]]
            ))
            coords = adsk.fusion.CustomGraphicsCoordinates.create(lst)
            lines: adsk.fusion.CustomGraphicsLines = cgGroup.addLines(coords, [0,1,2,3], True)
            lines.weight = 1.1

        return len(nodeIndiceSet)


    def export_meshes(
        self,
        entities: list,
        tolerance: float,
        lengthRatio: float,
        path: str,
        isOneFile: bool) -> None:

        basePath = pathlib.Path(path)
        baseDir = basePath.parent
        stem = self._get_valid_name(basePath.stem)
        suffix = basePath.suffix

        bodies = self._get_target_bodies(entities)
        stlSourceList = [self._get_mesh_source(mesh_data, lengthRatio, body.name) 
            for mesh_data, body in zip(self._get_mesh_datas(bodies, tolerance), bodies)]

        datas = []
        if isOneFile:
            expPath = baseDir / f'{stem}{suffix}'
            datas.append((str(expPath), '\n'.join(stlSourceList)))
        else:
            for body, source in zip(bodies, stlSourceList):
                bodyName = self._get_export_file_name(body)
                expPath = baseDir / f'{stem}_{bodyName}{suffix}'
                datas.append((str(expPath), source))

        [self._write_file(p, s) for p, s in datas]


    def _get_export_file_name(
        self,
        body: adsk.fusion.BRepBody) -> str:

        parent = None
        if body.assemblyContext:
            parent = body.assemblyContext
        else:
            parent = body.parentComponent

        return self._get_valid_name(f'{parent.name}_{body.name}')


    def _get_valid_name(
        self,
        txt) -> str:

        return re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', txt)


    def _get_triangleMesh(
        self,
        body: adsk.fusion.BRepBody,
        tolerance: float) -> adsk.fusion.TriangleMesh:

        meshCalc: adsk.fusion.TriangleMeshCalculator = body.meshManager.createMeshCalculator()
        meshCalc.surfaceTolerance = tolerance
        return meshCalc.calculate()


    def _get_mesh_data(
        self,
        body: adsk.fusion.BRepBody,
        tolerance: float) -> tuple:

        traMesh: adsk.fusion.TriangleMesh = self._get_triangleMesh(body, tolerance)

        nodeIndices = self._group_by_count(traMesh.nodeIndices, 3)

        points = self._group_by_list(
            traMesh.nodeCoordinates,
            nodeIndices
        )
        tmpNormals = self._group_by_list(
            traMesh.normalVectors,
            nodeIndices
        )
        normals = [self._synthesize_vectors(vs) for vs in tmpNormals]

        return (points, normals, nodeIndices)


    def _get_mesh_datas(
        self,
        bodies: list,
        tolerance: float) -> list:

        return [self._get_mesh_data(body, tolerance) for body in bodies]


    def _get_target_bodies(
        self,
        entities: list) -> list:

        # ******
        def is_Belonging(
            names: list,
            name: str) -> bool:

            return any([n in name for n in names])

        def remove_duplicates(
            lst: list) -> list:

            bodiesDict: dict = {}
            [bodiesDict.setdefault(body.entityToken, body) for body in lst]

            return list(bodiesDict.values())

        def get_all_show_body() -> list:
            self.app.activeProduct.rootComponent
            return root.findBRepUsingPoint(
                adsk.core.Point3D.create(0,0,0),
                adsk.fusion.BRepEntityTypes.BRepBodyEntityType,
                100000000000000,
                True
            )
    
        # *******
        comp_occ_types = [
            adsk.fusion.Component.classType,
            adsk.fusion.Occurrence.classType
        ]

        tmpBodies = []
        comp_occ_list = []
        for entity in entities:
            if entity.classType in comp_occ_types:
                comp_occ_list.append(entity)
            elif entity.isVisible:
                tmpBodies.append(entity)

        comp_occ_names = [co.name for co in comp_occ_list]

        root: adsk.fusion.Component = self.app.activeProduct.rootComponent
        allBodies: adsk.core.ObjectCollection = get_all_show_body()

        for body in allBodies:
            parent_fullpath = None
            if body.assemblyContext:
                parent_fullpath = f'{root.name}+{body.assemblyContext.fullPathName}'
            else:
                parent_fullpath = body.parentComponent.name

            if is_Belonging(comp_occ_names, parent_fullpath):
                tmpBodies.append(body)

        return remove_duplicates(tmpBodies)


    def _write_file(
        self,
        path: str,
        txt: str) -> None:

        with open(path, mode='w') as f:
            f.write(txt)


    def _get_mesh_source(
        self,
        mesh_data: tuple,
        lengthRatio: float,
        name: str) -> str:

        points, normals, _ = mesh_data
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