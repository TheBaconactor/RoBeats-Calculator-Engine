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
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
return {
    ["new"] = function(_, p_u_5, _, p_u_6, p_u_7) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_2, (copy 4): v_u_4 ]]
        local v8 = v_u_3:new()
        local v_u_9 = false
        local v_u_10 = p_u_5:get_child_part()
        local v_u_11 = nil
        local v_u_12 = nil
        local v_u_13 = nil
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        v8.cons = function(p18) --[[ Name: cons ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_10, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_14, (ref 6): v_u_17, (ref 7): v_u_13 ]]
            v_u_15 = v_u_10.SurfaceGui.Frame.Pane
            v_u_11 = v_u_15.Icon
            v_u_12 = v_u_15.IconOverlay
            v_u_14 = v_u_15.CopiesDisplay
            v_u_17 = v_u_15.TextDisplay
            v_u_13 = v_u_15:FindFirstChild("ExtraInfoIcon")
            if v_u_13 then
                v_u_13.Visible = false
            end;
            p18:set_selected(nil, false)
            p18:layout()
        end;
        v8.set_info = function(_, p19, p20, p21) --[[ Name: set_info ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_11, (ref 3): v_u_12, (ref 4): v_u_1, (ref 5): v_u_14, (ref 6): v_u_17, (ref 7): v_u_13 ]]
            v_u_16 = p19
            v_u_11.Image = p20
            v_u_12.Image = v_u_1:transparent_assetid()
            v_u_14.Text = string.format("%d", p21)
            v_u_11.Visible = true
            v_u_12.Visible = true
            v_u_17.Visible = false
            if v_u_13 then
                v_u_13.Visible = false
            end;
        end;
        v8.set_info_text = function(_, p22, p23, p24) --[[ Name: set_info_text ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_14, (ref 4): v_u_11, (ref 5): v_u_12, (ref 6): v_u_13 ]]
            v_u_16 = p22
            v_u_17.Text = p23
            v_u_14.Text = string.format("%d", p24)
            v_u_11.Visible = false
            v_u_12.Visible = false
            v_u_17.Visible = true
            if v_u_13 then
                v_u_13.Visible = false
            end;
        end;
        v8.set_extra_info_icon = function(_, p25) --[[ Name: set_extra_info_icon ]] --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            if v_u_13 then
                v_u_13.Visible = true
                v_u_13.Image = p25
            end;
        end;
        v8.get_data = function(_) --[[ Name: get_data ]] --[[ Line: 76 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            return v_u_16;
        end;
        v8.get_icon_and_overlay = function(_) --[[ Name: get_icon_and_overlay ]] --[[ Line: 78 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12 ]]
            return v_u_11, v_u_12;
        end;
        v8.update = function(_, p26, _) --[[ Name: update ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_5, (ref 3): v_u_2 ]]
            p_u_5:set_scale(v_u_2:Expt(p_u_5:get_scale(), v_u_9 == true and 1.1 or 1, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p26))
        end;
        v8.layout = function(p27) --[[ Name: layout ]] --[[ Line: 95 ]]
            --[[ Upvalues: (copy 1): p_u_5, (copy 2): v_u_10 ]]
            p_u_5:layout()
            p27._native_size = v_u_10.Size
            p27._size = p27._native_size
        end;
        local v_u_28 = true
        v8.set_enabled = function(p29, p30) --[[ Name: set_enabled ]] --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_28 ]]
            if p30 == false then
                v_u_9 = false
            else
                p29:set_alpha(1)
            end;
            v_u_28 = p30
            return p29;
        end;
        v8.get_enabled = function(_) --[[ Name: get_enabled ]] --[[ Line: 111 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28;
        end;
        v8.set_visible = function(p31, p32) --[[ Name: set_visible ]] --[[ Line: 113 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            if p32 == true then
                v_u_10.SurfaceGui.Enabled = true
            else
                v_u_10.SurfaceGui.Enabled = false
            end;
            p31:set_enabled(p32)
            return p31;
        end;
        v8.is_selectable = function(_) --[[ Name: is_selectable ]] --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28;
        end;
        v8.get_selected = function(_) --[[ Name: get_selected ]] --[[ Line: 127 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end;
        v8.trigger_element = function(p33, p34) --[[ Name: trigger_element ]] --[[ Line: 131 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_6, (copy 3): p_u_7, (ref 4): v_u_16 ]]
            p33:trigger_element_visual()
            p34._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
            p_u_6:list_element_pressed(p33, p_u_7, v_u_16)
        end;
        v8.trigger_element_visual = function(_) --[[ Name: trigger_element_visual ]] --[[ Line: 137 ]]
            --[[ Upvalues: (copy 1): p_u_5 ]]
            p_u_5:set_scale(1.5)
        end;
        v8.set_highlighted = function(_, p35) --[[ Name: set_highlighted ]] --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_1, (ref 3): v_u_14, (ref 4): v_u_17 ]]
            if p35 then
                v_u_15.Image = v_u_1:get_inventory_item_selected_assetid()
                v_u_14.TextColor3 = Color3.fromRGB(10, 10, 10)
                v_u_17.TextColor3 = Color3.fromRGB(10, 10, 10)
            else
                v_u_15.Image = v_u_1:get_inventory_item_assetid()
                v_u_14.TextColor3 = Color3.fromRGB(254, 255, 249)
                v_u_17.TextColor3 = Color3.fromRGB(254, 255, 249)
            end;
        end;
        v8.set_selected = function(_, _, p36) --[[ Name: set_selected ]] --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): v_u_10, (copy 3): p_u_5 ]]
            v_u_9 = p36
            if v_u_9 then
                v_u_10.SurfaceGui.ZOffset = 1500 + p_u_5:get_child_id()
            else
                v_u_10.SurfaceGui.ZOffset = 1000 + p_u_5:get_child_id()
            end;
        end;
        v8.get_native_size = function(p37) --[[ Name: get_native_size ]] --[[ Line: 164 ]]
            return p37._native_size;
        end;
        v8.get_size = function(p38) --[[ Name: get_size ]] --[[ Line: 167 ]]
            return p38._size;
        end;
        v8.set_size = function(p39, p40) --[[ Name: set_size ]] --[[ Line: 170 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            p39._size = p40
            v_u_10.Size = Vector3.new(p40.X, p40.Y, 0)
        end;
        v8.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 174 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            return v_u_10.Position;
        end;
        local v_u_41 = 1
        v8.set_parent_alpha = function(_, p42) --[[ Name: set_parent_alpha ]] --[[ Line: 179 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41 = p42
        end;
        local v_u_43 = 1
        v8.set_alpha = function(_, p44) --[[ Name: set_alpha ]] --[[ Line: 184 ]]
            --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_1, (copy 3): v_u_10, (ref 4): v_u_41 ]]
            if p44 ~= v_u_43 then
                v_u_43 = p44
                v_u_1:obj_set_alpha(v_u_10, v_u_43, v_u_41)
            end;
        end;
        v8:cons()
        return v8;
    end
};
