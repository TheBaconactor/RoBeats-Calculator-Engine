-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:52 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Menu.CycleElementBase)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
return {
    ["List"] = {
        ["Inventory"] = 1,
        ["PlayerOffer"] = 2,
        ["TargetOffer"] = 3
    },
    ["new"] = function(_, p_u_5, _, p_u_6, _, p_u_7) --[[ Name: new ]] --[[ Line: 17 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_1 ]]
        local v8 = v_u_3:new()
        local v_u_9 = false
        local v_u_10 = p_u_5:get_child_part()
        local v_u_11 = nil
        local v_u_12 = nil
        local v_u_13 = nil
        local v_u_14 = -1
        v8.cons = function(p15) --[[ Name: cons ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_10, (ref 3): v_u_12, (ref 4): v_u_13 ]]
            v_u_11 = v_u_10.SurfaceGui.Frame.Icon
            v_u_12 = v_u_10.SurfaceGui.Frame.CopiesDisplay
            v_u_13 = v_u_10.SurfaceGui.Frame.NameDisplay
            p15:set_selected(nil, false)
            p15:layout()
        end;
        v8.set_material_id_and_count = function(_, p16, p17) --[[ Name: set_material_id_and_count ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_13, (ref 3): v_u_4, (ref 4): v_u_11, (ref 5): v_u_12 ]]
            v_u_14 = p16
            v_u_13.Text = v_u_4:singleton():get_material_name(p16)
            v_u_11.Image = v_u_4:singleton():get_material_icon(p16)
            v_u_12.Text = string.format("%d", p17)
        end;
        v8.update = function(_, p18, _) --[[ Name: update ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_5, (ref 3): v_u_2 ]]
            p_u_5:set_scale(v_u_2:Expt(p_u_5:get_scale(), v_u_9 == true and 1.1 or 1, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p18))
        end;
        v8.layout = function(p19) --[[ Name: layout ]] --[[ Line: 56 ]]
            --[[ Upvalues: (copy 1): p_u_5, (copy 2): v_u_10 ]]
            p_u_5:layout()
            p19._native_size = v_u_10.Size
            p19._size = p19._native_size
        end;
        local v_u_20 = true
        v8.set_enabled = function(p21, p22) --[[ Name: set_enabled ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_20 ]]
            if p22 == false then
                v_u_9 = false
            else
                p21:set_alpha(1)
            end;
            v_u_20 = p22
            return p21;
        end;
        v8.set_visible = function(p23, p24) --[[ Name: set_visible ]] --[[ Line: 73 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            if p24 == true then
                v_u_10.SurfaceGui.Enabled = true
            else
                v_u_10.SurfaceGui.Enabled = false
            end;
            p23:set_enabled(p24)
            return p23;
        end;
        v8.is_selectable = function(_) --[[ Name: is_selectable ]] --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        v8.get_selected = function(_) --[[ Name: get_selected ]] --[[ Line: 87 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end;
        v8.trigger_element = function(_, _) --[[ Name: trigger_element ]] --[[ Line: 91 ]]
            --[[ Upvalues: (copy 1): p_u_5, (copy 2): p_u_7, (copy 3): p_u_6, (ref 4): v_u_14 ]]
            p_u_5:set_scale(1.5)
            p_u_7:list_element_pressed(p_u_6, v_u_14)
        end;
        v8.set_selected = function(_, _, p25) --[[ Name: set_selected ]] --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): v_u_10, (copy 3): p_u_5 ]]
            v_u_9 = p25
            if v_u_9 then
                v_u_10.SurfaceGui.ZOffset = 1500 + p_u_5:get_child_id()
            else
                v_u_10.SurfaceGui.ZOffset = 1000 + p_u_5:get_child_id()
            end;
        end;
        v8.get_native_size = function(p26) --[[ Name: get_native_size ]] --[[ Line: 106 ]]
            return p26._native_size;
        end;
        v8.get_size = function(p27) --[[ Name: get_size ]] --[[ Line: 109 ]]
            return p27._size;
        end;
        v8.set_size = function(p28, p29) --[[ Name: set_size ]] --[[ Line: 112 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            p28._size = p29
            v_u_10.Size = Vector3.new(p29.X, p29.Y, 0)
        end;
        v8.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 116 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            return v_u_10.Position;
        end;
        local v_u_30 = 1
        v8.set_alpha = function(_, p31) --[[ Name: set_alpha ]] --[[ Line: 121 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_1, (copy 3): v_u_10 ]]
            if p31 ~= v_u_30 then
                v_u_30 = p31
                v_u_1:obj_set_alpha(v_u_10, v_u_30, 1)
            end;
        end;
        v8:cons()
        return v8;
    end
};
