-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:03 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Menu.CycleElementBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Local.DebugOut)
return {
    ["new"] = function(_, p_u_5, p_u_6, p_u_7) --[[ Name: new ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_1 ]]
        local v8 = v_u_3:new()
        local v_u_9 = false
        local v_u_10 = 0
        local v_u_11 = 0
        local v_u_12 = 1
        v8.set_scale = function(p13, p14) --[[ Name: set_scale ]] --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            v_u_12 = p14
            return p13;
        end;
        local v_u_15 = 0
        local v_u_16 = p_u_5.PrimaryPart:FindFirstChild("SurfaceGui")
        local v_u_17 = not v_u_16 and 0 or v_u_16.ZOffset
        local v_u_18 = v_u_17 + 500
        v8.set_visible = function(p19, p20) --[[ Name: set_visible ]] --[[ Line: 30 ]]
            --[[ Upvalues: (copy 1): v_u_16 ]]
            v_u_16.Enabled = p20
            p19:set_selectable(p20)
        end;
        local v_u_21 = true
        v8.set_auto_zoffset_behaviour = function(p22, p23) --[[ Name: set_auto_zoffset_behaviour ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21 = p23
            return p22;
        end;
        local v_u_24 = v_u_4:new(0.5, 0.5)
        local v_u_25 = v_u_4:new(0.5, 0.5)
        v8.set_position_nxy = function(p26, p27, p28) --[[ Name: set_position_nxy ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): v_u_24 ]]
            v_u_24:set(p27, p28)
            return p26;
        end;
        v8.get_position_nxy = function(_) --[[ Name: get_position_nxy ]] --[[ Line: 47 ]]
            --[[ Upvalues: (copy 1): v_u_24 ]]
            return v_u_24;
        end;
        v8.set_anchor_rnxy = function(p29, p30, p31) --[[ Name: set_anchor_rnxy ]] --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): v_u_25 ]]
            v_u_25:set(p30, p31)
            return p29;
        end;
        local v_u_32 = v_u_4:new(0, 0)
        v8.get_position_offset_xy = function(_) --[[ Name: get_position_offset_xy ]] --[[ Line: 55 ]]
            --[[ Upvalues: (copy 1): v_u_32 ]]
            return v_u_32;
        end;
        v8.set_position_offset_xy = function(p33, p34, p35) --[[ Name: set_position_offset_xy ]] --[[ Line: 56 ]]
            --[[ Upvalues: (copy 1): v_u_32 ]]
            v_u_32:set(p34, p35)
            return p33;
        end;
        local v_u_36 = false
        local v_u_37 = v_u_4:new(0, 0)
        v8.set_max_nxy = function(p38, p39, p40) --[[ Name: set_max_nxy ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): v_u_36, (copy 2): v_u_37 ]]
            v_u_36 = true
            v_u_37:set(p39, p40)
            return p38;
        end;
        local v_u_41 = nil
        v8.get_pre_layout_fn = function(_) --[[ Name: get_pre_layout_fn ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            return v_u_41;
        end;
        v8.set_pre_layout_fn = function(p42, p43) --[[ Name: set_pre_layout_fn ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41 = p43
            p43()
            return p42;
        end;
        local v_u_44 = nil
        v8.cons = function(p45) --[[ Name: cons ]] --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): v_u_44, (copy 2): p_u_5 ]]
            v_u_44 = p_u_5.PrimaryPart
            p45._native_size = v_u_44.Size
            p45._size = v_u_44.Size
            p45:layout()
        end;
        v8.layout = function(p46) --[[ Name: layout ]] --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): v_u_36, (copy 2): p_u_6, (copy 3): v_u_37, (ref 4): v_u_12, (ref 5): v_u_44, (ref 6): v_u_41, (copy 7): p_u_5, (copy 8): v_u_24, (copy 9): v_u_25, (copy 10): v_u_32, (ref 11): v_u_15 ]]
            if v_u_36 == true then
                p_u_6:uiobj_rescale_to_max_nxy(p46, v_u_37._x, v_u_37._y, v_u_12)
            else
                v_u_44.Size = p46._native_size * v_u_12
            end;
            p46._size = v_u_44.Size
            if v_u_41 ~= nil then
                v_u_41()
            end;
            p_u_5:SetPrimaryPartCFrame(p_u_6:get_cframe({
                ["PositionNXY"] = Vector2.new(v_u_24._x, v_u_24._y),
                ["OffsetXYZ"] = p46:anchored_offset(v_u_25._x, v_u_25._y) + Vector3.new(v_u_32._x, v_u_32._y, 0),
                ["LocalRotationOffset"] = Vector3.new(0, 0, v_u_15)
            }))
        end;
        local v_u_47 = true
        v8.set_selectable = function(p48, p49) --[[ Name: set_selectable ]] --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_47 ]]
            v_u_47 = p49
            return p48;
        end;
        local v_u_50 = 10
        v8.set_selected_rotation_amplitude = function(p51, p52) --[[ Name: set_selected_rotation_amplitude ]] --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): v_u_50 ]]
            v_u_50 = p52
            return p51;
        end;
        local v_u_53 = 1.25
        v8.set_selected_tar_scale = function(p54, p55) --[[ Name: set_selected_tar_scale ]] --[[ Line: 113 ]]
            --[[ Upvalues: (ref 1): v_u_53 ]]
            v_u_53 = p55
            return p54;
        end;
        local v_u_56 = false
        v8.set_passive_anim = function(p57) --[[ Name: set_passive_anim ]] --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_56 ]]
            v_u_56 = true
            return p57;
        end;
        v8.update = function(p58, p59, _) --[[ Name: update ]] --[[ Line: 124 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_47, (ref 3): v_u_53, (ref 4): v_u_10, (ref 5): v_u_50, (ref 6): v_u_2, (ref 7): v_u_56, (ref 8): v_u_21, (copy 9): v_u_16, (copy 10): v_u_18, (ref 11): v_u_17, (ref 12): v_u_11, (ref 13): v_u_12, (ref 14): v_u_15 ]]
            local v60 = 1
            local v61 = 0
            if v_u_9 == true and v_u_47 == true then
                v60 = v_u_53
                v61 = math.sin(v_u_10) * v_u_50
                v_u_10 = v_u_2:IncrementWrap(v_u_10, 0.05 * p59, 6.283185307179586)
            elseif v_u_56 == true then
                v61 = math.sin(v_u_10) * v_u_50 * 0.5
                v_u_10 = v_u_2:IncrementWrap(v_u_10, 0.025 * p59, 6.283185307179586)
            end;
            if v_u_21 == true and v_u_16 ~= nil then
                if v_u_9 then
                    v_u_16.ZOffset = v_u_18
                else
                    v_u_16.ZOffset = v_u_17
                end;
            end;
            local v62 = v60 + v_u_11
            v_u_11 = v_u_2:Expt(v_u_11, 0, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p59)
            v_u_12 = v_u_2:Expt(v_u_12, v62, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p59)
            v_u_15 = v_u_2:Expt(v_u_15, v61, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p59)
            p58:layout()
        end;
        v8.is_selectable = function(_) --[[ Name: is_selectable ]] --[[ Line: 174 ]]
            --[[ Upvalues: (ref 1): v_u_47 ]]
            return v_u_47;
        end;
        v8.get_selected = function(_) --[[ Name: get_selected ]] --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end;
        v8.trigger_element = function(_, _) --[[ Name: trigger_element ]] --[[ Line: 182 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_11, (ref 3): v_u_1 ]]
            p_u_7()
            v_u_11 = v_u_1:clamp(v_u_11 + 1, 0, 2)
        end;
        v8.set_selected = function(_, _, p63) --[[ Name: set_selected ]] --[[ Line: 187 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            v_u_9 = p63
        end;
        v8.get_native_size = function(p64) --[[ Name: get_native_size ]] --[[ Line: 191 ]]
            return p64._native_size;
        end;
        v8.get_size = function(p65) --[[ Name: get_size ]] --[[ Line: 194 ]]
            return p65._size;
        end;
        v8.set_size = function(p66, p67) --[[ Name: set_size ]] --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): v_u_44 ]]
            p66._size = p67
            v_u_44.Size = Vector3.new(p67.X, p67.Y, 0)
        end;
        v8.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 201 ]]
            --[[ Upvalues: (ref 1): v_u_44 ]]
            return v_u_44.Position;
        end;
        v8.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 204 ]]
            --[[ Upvalues: (ref 1): v_u_44 ]]
            return v_u_44.SurfaceGui;
        end;
        v8:cons()
        return v8;
    end
};
