-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:01 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.AssertType)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPRange)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = {
    ["ZoneName"] = {
        ["Club"] = 1,
        ["MusicShop"] = 2,
        ["CompeteTower"] = 3,
        ["GearShop"] = 4,
        ["Marketplace"] = 5,
        ["CrossroadsStageEvent"] = 6,
        ["GuildBuilding"] = 7,
        ["OnGround"] = 8
    },
    ["BaseZone"] = {},
    ["BlockZone"] = {},
    ["CylinderZone"] = {}
}
v_u_5.BaseZone.new = function(_) --[[ Name: new ]] --[[ Line: 23 ]]
    return {
        ["contains_point"] = function(_, _) --[[ Name: contains_point ]] --[[ Line: 25 ]]
            return false;
        end,
        ["to_string"] = function(_) --[[ Name: to_string ]] --[[ Line: 26 ]]
            return "BaseZone";
        end
    };
end;
v_u_5.BlockZone.new = function(_, p_u_6) --[[ Name: new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_2, (copy 3): v_u_1 ]]
    local v7 = v_u_5.BaseZone:new()
    local v_u_8 = nil
    local v_u_9 = nil
    local v_u_10 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 35 ]]
        --[[ Upvalues: (copy 1): p_u_6, (ref 2): v_u_2, (ref 3): v_u_8, (ref 4): v_u_1, (ref 5): v_u_9, (ref 6): v_u_10 ]]
        if p_u_6.Orientation ~= Vector3.new() then
            v_u_2:warnf("IntersectZoneManager.BlockZone orientation not <0,0,0>")
        end;
        v_u_8 = v_u_1:new(p_u_6.Position.X - p_u_6.Size.X / 2, p_u_6.Position.X + p_u_6.Size.X / 2)
        v_u_9 = v_u_1:new(p_u_6.Position.Y - p_u_6.Size.Y / 2, p_u_6.Position.Y + p_u_6.Size.Y / 2)
        v_u_10 = v_u_1:new(p_u_6.Position.Z - p_u_6.Size.Z / 2, p_u_6.Position.Z + p_u_6.Size.Z / 2)
    end;
    v7.contains_point = function(_, p11) --[[ Name: contains_point ]] --[[ Line: 42 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (ref 3): v_u_10 ]]
        local v12 = v_u_8:contains_eq(p11.X) and v_u_9:contains_eq(p11.Y)
        if v12 then
            v12 = v_u_10:contains_eq(p11.Z)
        end;
        return v12;
    end;
    v7.to_string = function(_) --[[ Name: to_string ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (ref 3): v_u_10 ]]
        return string.format("BlockZone x(%.2f,%.2f) y(%.2f,%.2f) z(%.2f,%.2f)", v_u_8:min(), v_u_8:max(), v_u_9:min(), v_u_9:max(), v_u_10:min(), v_u_10:max());
    end;
    f_cons()
    return v7;
end;
v_u_5.CylinderZone.new = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 55 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_2, (copy 3): v_u_1 ]]
    local v14 = v_u_5.BaseZone:new()
    local v_u_15 = nil
    local v_u_16 = 0
    local v_u_17 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 62 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_2, (ref 3): v_u_15, (ref 4): v_u_1, (ref 5): v_u_16, (ref 6): v_u_17 ]]
        if p_u_13.Orientation ~= Vector3.new(0, 0, 90) then
            v_u_2:warnf("IntersectZoneManager.CylinderZone orientation not <0,0,90>")
        end;
        if p_u_13.Size.Y ~= p_u_13.Size.Z then
            v_u_2:warnf("IntersectZoneManager.CylinderZone size.Y <> size.Z")
        end;
        v_u_15 = v_u_1:new(p_u_13.Position.Y - p_u_13.Size.X / 2, p_u_13.Position.Y + p_u_13.Size.X / 2)
        v_u_16 = p_u_13.Size.Y / 2
        v_u_17 = Vector2.new(p_u_13.Position.X, p_u_13.Position.Z)
    end;
    v14.contains_point = function(_, p18) --[[ Name: contains_point ]] --[[ Line: 70 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_15, (ref 3): v_u_16 ]]
        local l_Magnitude_0 = (v_u_17 - Vector2.new(p18.X, p18.Z)).Magnitude
        local v19 = v_u_15:contains_eq(p18.Y)
        if v19 then
            v19 = l_Magnitude_0 <= v_u_16
        end;
        return v19;
    end;
    v14.to_string = function(_) --[[ Name: to_string ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_16, (ref 3): v_u_15 ]]
        return string.format("CylinderZone xz(%.2f,0,%.2f) radius(%.2f) _range_y(%.2f,%.2f)", v_u_17.X, v_u_17.Y, v_u_16, v_u_15:min(), v_u_15:max());
    end;
    f_cons()
    return v14;
end;
v_u_5.new = function(_) --[[ Name: new ]] --[[ Line: 83 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5, (copy 3): v_u_3, (copy 4): v_u_2 ]]
    local v_u_20 = {}
    local v_u_21 = v_u_4:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 88 ]]
        --[[ Upvalues: (copy 1): v_u_21, (ref 2): v_u_5, (copy 3): v_u_20, (ref 4): v_u_3 ]]
        v_u_21:add(v_u_5.ZoneName.Club, v_u_20:intersect_zone_from_part(v_u_3:get_intersect_zones_root().Club))
        v_u_21:add(v_u_5.ZoneName.MusicShop, v_u_20:intersect_zone_from_part(v_u_3:get_intersect_zones_root().MusicShop))
        v_u_21:add(v_u_5.ZoneName.CompeteTower, v_u_20:intersect_zone_from_part(v_u_3:get_intersect_zones_root().CompeteTower))
        v_u_21:add(v_u_5.ZoneName.GearShop, v_u_20:intersect_zone_from_part(v_u_3:get_intersect_zones_root().GearShop))
        v_u_21:add(v_u_5.ZoneName.Marketplace, v_u_20:intersect_zone_from_part(v_u_3:get_intersect_zones_root().Marketplace))
        v_u_21:add(v_u_5.ZoneName.CrossroadsStageEvent, v_u_20:intersect_zone_from_part(v_u_3:get_intersect_zones_root().CrossroadsStageEvent))
        v_u_21:add(v_u_5.ZoneName.GuildBuilding, v_u_20:intersect_zone_from_part(v_u_3:get_intersect_zones_root().GuildBuilding))
        v_u_21:add(v_u_5.ZoneName.OnGround, v_u_20:intersect_zone_from_part(v_u_3:get_intersect_zones_root().OnGround))
    end;
    local v_u_22 = v_u_4:new()
    v_u_20.get_intersecting_zones_for_point = function(_, p23, p24) --[[ Name: get_intersecting_zones_for_point ]] --[[ Line: 124 ]]
        --[[ Upvalues: (copy 1): v_u_22, (copy 2): v_u_21 ]]
        v_u_22:clear()
        if p24 == nil then
            for v25, v26 in v_u_21:key_itr() do
                if v26:contains_point(p23) then
                    v_u_22:add(v25, true)
                end;
            end;
        else
            for v27, _ in p24:key_itr() do
                if v_u_21:contains(v27) and v_u_21:get(v27):contains_point(p23) then
                    v_u_22:add(v27, true)
                end;
            end;
        end;
        return v_u_22;
    end;
    v_u_20.intersect_zone_from_part = function(_, p28) --[[ Name: intersect_zone_from_part ]] --[[ Line: 144 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_2 ]]
        if p28.Shape == Enum.PartType.Block then
            return v_u_5.BlockZone:new(p28);
        end;
        if p28.Shape == Enum.PartType.Cylinder then
            return v_u_5.CylinderZone:new(p28);
        end;
        v_u_2:errf("IntersectZoneManager:intersect_zone_from_part invalid")
    end;
    v_u_20.get_intersect_zone_for_zonename = function(_, p29) --[[ Name: get_intersect_zone_for_zonename ]] --[[ Line: 154 ]]
        --[[ Upvalues: (copy 1): v_u_21 ]]
        return v_u_21:get(p29);
    end;
    f_cons()
    return v_u_20;
end;
return v_u_5;
