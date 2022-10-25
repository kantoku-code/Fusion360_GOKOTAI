#Fusion360API Python

import adsk.core
import adsk.fusion
import itertools
import random

class ColorfulWireFrameFactry:
    def __init__(self) -> None:
        self.rgb = RgbContainer()
    
    def drawCG(self):
        app: adsk.core.Application = adsk.core.Application.get()
        des: adsk.fusion.Design = app.activeProduct
        root: adsk.fusion.Component = des.rootComponent

        bodies = root.findBRepUsingPoint(
            adsk.core.Point3D.create(0,0,0),
            adsk.fusion.BRepEntityTypes.BRepBodyEntityType,
            1000000000000000,
            True
        )

        tmpMgr: adsk.fusion.TemporaryBRepManager = adsk.fusion.TemporaryBRepManager.get()
        tokens = [b.entityToken for b in bodies]
        clones = [tmpMgr.copy(b)for b in bodies]
        edgesGroup = [b.edges for b in clones]

        for edges, token in zip(edgesGroup, tokens):
            cgGroup: adsk.fusion.CustomGraphicsGroup = root.customGraphicsGroups.add()
            color = self.rgb.getColor(token)
            for edge in edges:
                try:
                    cgCurve: adsk.fusion.CustomGraphicsCurve= cgGroup.addCurve(edge.geometry)
                    cgCurve.weight = 2
                    cgCurve.color = color
                except:
                    pass
            adsk.doEvents()
            app.activeViewport.refresh()


    def drawCGBody(self, body: adsk.fusion.BRepBody):
        app: adsk.core.Application = adsk.core.Application.get()
        des: adsk.fusion.Design = app.activeProduct
        root: adsk.fusion.Component = des.rootComponent

        # bodies = root.findBRepUsingPoint(
        #     adsk.core.Point3D.create(0,0,0),
        #     adsk.fusion.BRepEntityTypes.BRepBodyEntityType,
        #     1000000000000000,
        #     True
        # )

        tmpMgr: adsk.fusion.TemporaryBRepManager = adsk.fusion.TemporaryBRepManager.get()
        token = body.entityToken
        clone = tmpMgr.copy(body)
        # edgesGroup = [b.edges for b in clones]


        # for edges, token in zip(edgesGroup, tokens):
        cgGroup: adsk.fusion.CustomGraphicsGroup = root.customGraphicsGroups.add()
        color = self.rgb.getColor(token)
        for edge in clone.edges:
            try:
                cgCurve: adsk.fusion.CustomGraphicsCurve= cgGroup.addCurve(edge.geometry)
                cgCurve.weight = 2
                cgCurve.color = color
            except:
                pass

        adsk.doEvents()
        app.activeViewport.refresh()


    def drawTest(self):
        app: adsk.core.Application = adsk.core.Application.get()
        des: adsk.fusion.Design = app.activeProduct
        root: adsk.fusion.Component = des.rootComponent

        bodies = root.findBRepUsingPoint(
            adsk.core.Point3D.create(0,0,0),
            adsk.fusion.BRepEntityTypes.BRepBodyEntityType,
            1000000000000000,
            True
        )

        for body in bodies:
            body: adsk.fusion.BRepBody
            body.opacity = 0.3

        # tmpMgr: adsk.fusion.TemporaryBRepManager = adsk.fusion.TemporaryBRepManager.get()
        # tokens = [b.entityToken for b in bodies]
        # clones = [tmpMgr.copy(b)for b in bodies]
        # edgesGroup = [b.edges for b in clones]

        # for edges, token in zip(edgesGroup, tokens):
        #     cgGroup: adsk.fusion.CustomGraphicsGroup = root.customGraphicsGroups.add()
        #     color = self.rgb.getColor(token)
        #     for edge in edges:
        #         try:
        #             cgCurve: adsk.fusion.CustomGraphicsCurve= cgGroup.addCurve(edge.geometry)
        #             cgCurve.weight = 2
        #             cgCurve.color = color
        #         except:
        #             pass
        #     adsk.doEvents()
        #     app.activeViewport.refresh()


class RgbContainer():
    def __init__(self) -> None:
        self.bodiesDict = {}
        self.rgbSets = set(itertools.permutations(range(0, 256, 5), 3))


    def getColor(self, token) -> adsk.fusion.CustomGraphicsSolidColorEffect:
        if token in self.bodiesDict:
            return self.bodiesDict[token]
        else:
            color: adsk.fusion.CustomGraphicsSolidColorEffect = self.__pop__()
            self.bodiesDict[token] = color

            return color

    def __pop__(self) -> adsk.fusion.CustomGraphicsSolidColorEffect:
        rgb = random.sample(self.rgbSets, 1)
        self.rgbSets = self.rgbSets.difference(set(rgb))

        return adsk.fusion.CustomGraphicsSolidColorEffect.create(
            adsk.core.Color.create(rgb[0][0], rgb[0][1], rgb[0][2], 255)
        )