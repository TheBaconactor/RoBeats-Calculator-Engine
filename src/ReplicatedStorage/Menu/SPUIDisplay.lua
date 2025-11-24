-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:03 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Menu.CycleElementBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_3 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.LVector3)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
return {
    ["new"] = function(_, p_u_5, p_u_6) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_3 ]]
        local v7 = v_u_1:SPUIObjectBase()
        local v8
        if p_u_5.PrimaryPart then
            v8 = p_u_5.PrimaryPart:FindFirstChild("SurfaceGui")
        else
            v8 = nil
        end;
        local v_u_9 = not v8 and 0 or v8.ZOffset
        local v_u_10 = 1
        v7.get_alloc_child_id = function(_) --[[ Name: get_alloc_child_id ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_10, (ref 3): v_u_9 ]]
            if v_u_4.DoZOffsetChildren ~= true then
                return 0;
            end;
            local v11 = v_u_10
            v_u_10 = v_u_10 + 1
            return v11 + v_u_9;
        end;
        v7.cons = function(p12) --[[ Name: cons ]] --[[ Line: 38 ]]
            p12._native_size = p12:get_part().Size
            p12._size = p12:get_part().Size
        end;
        v7.get_part = function(_) --[[ Name: get_part ]] --[[ Line: 46 ]]
            --[[ Upvalues: (copy 1): p_u_5 ]]
            return p_u_5.PrimaryPart;
        end;
        local v_u_13 = Vector3.new(1, 1, 1)
        v7.set_scale = function(p14, p15, p16) --[[ Name: set_scale ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            v_u_13 = Vector3.new(p15, p16, 1)
            return p14;
        end;
        local v_u_17 = v_u_2:new(0.5, 0.5)
        local v_u_18 = v_u_2:new(0.5, 0.5)
        v7.set_position_nxy = function(p19, p20, p21) --[[ Name: set_position_nxy ]] --[[ Line: 58 ]]
            --[[ Upvalues: (copy 1): v_u_17 ]]
            v_u_17:set(p20, p21)
            return p19;
        end;
        v7.get_position_nxy = function(_) --[[ Name: get_position_nxy ]] --[[ Line: 62 ]]
            --[[ Upvalues: (copy 1): v_u_17 ]]
            return v_u_17;
        end;
        v7.set_anchor_rnxy = function(p22, p23, p24) --[[ Name: set_anchor_rnxy ]] --[[ Line: 64 ]]
            --[[ Upvalues: (copy 1): v_u_18 ]]
            v_u_18:set(p23, p24)
            return p22;
        end;
        local v_u_25 = v_u_2:new(0, 0)
        v7.set_position_offset_xy = function(p26, p27, p28) --[[ Name: set_position_offset_xy ]] --[[ Line: 70 ]]
            --[[ Upvalues: (copy 1): v_u_25 ]]
            v_u_25:set(p27, p28)
            return p26;
        end;
        v7.get_position_offset_xy = function(_) --[[ Name: get_position_offset_xy ]] --[[ Line: 74 ]]
            --[[ Upvalues: (copy 1): v_u_25 ]]
            return v_u_25;
        end;
        v7.layout = function(p29) --[[ Name: layout ]] --[[ Line: 76 ]]
            --[[ Upvalues: (copy 1): p_u_5, (copy 2): p_u_6, (copy 3): v_u_17, (copy 4): v_u_18, (copy 5): v_u_25 ]]
            p_u_5.PrimaryPart.CFrame = p_u_6:get_cframe({
                ["PositionNXY"] = Vector2.new(v_u_17._x, v_u_17._y),
                ["OffsetXYZ"] = p29:anchored_offset(v_u_18._x, v_u_18._y) + Vector3.new(v_u_25._x, v_u_25._y, 0),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
        end;
        v7.get_native_size = function(p30) --[[ Name: get_native_size ]] --[[ Line: 84 ]]
            return p30._native_size;
        end;
        v7.get_size = function(p31) --[[ Name: get_size ]] --[[ Line: 87 ]]
            return p31._size;
        end;
        v7.set_size = function(p32, p33) --[[ Name: set_size ]] --[[ Line: 90 ]]
            p32._size = p33
            if p32:get_part() then
                p32:get_part().Size = Vector3.new(p33.X, p33.Y, 0)
            end;
        end;
        v7.get_pos = function(p34) --[[ Name: get_pos ]] --[[ Line: 96 ]]
            return p34:get_part().Position;
        end;
        v7.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3:errf("SPUIButton get_sgui not implemented")
            return nil;
        end;
        v7:cons()
        return v7;
    end
};
