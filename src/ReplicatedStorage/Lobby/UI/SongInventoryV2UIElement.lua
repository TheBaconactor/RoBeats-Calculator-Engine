-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:50 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Menu.CycleElementBase)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
return {
    ["new"] = function(_, p_u_6, _, p_u_7) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_5, (copy 5): v_u_1 ]]
        local v8 = v_u_3:new()
        local v_u_9 = p_u_6:get_child_part()
        local v_u_10 = false
        local v_u_11 = 0
        local v_u_12 = 0
        local v_u_13 = nil
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        v8.cons = function(p20) --[[ Name: cons ]] --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_6, (ref 3): v_u_14, (ref 4): v_u_15, (ref 5): v_u_16, (ref 6): v_u_17, (ref 7): v_u_18, (ref 8): v_u_19 ]]
            v_u_13 = p_u_6:get_child_part().SurfaceGui.Frame.Pane
            v_u_14 = p_u_6:get_child_part().SurfaceGui.Frame.PaneSelected
            v_u_15 = p_u_6:get_child_part().SurfaceGui.Frame.Pane.AlbumArt
            v_u_16 = p_u_6:get_child_part().SurfaceGui.Frame.Pane.AlbumArtOverlay
            v_u_17 = p_u_6:get_child_part().SurfaceGui.Frame.Pane.ColorSection.PrimaryColorIcon
            v_u_18 = p_u_6:get_child_part().SurfaceGui.Frame.Pane.ColorSection.SecondaryColorIcon
            v_u_19 = p_u_6:get_child_part().SurfaceGui.Frame.Pane.CopiesDisplay
            p20:set_alpha(0)
            p20:layout()
        end;
        v8.layout = function(p21) --[[ Name: layout ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): p_u_6, (copy 2): v_u_9 ]]
            p_u_6:layout()
            p21._native_size = v_u_9.Size
            p21._size = p21._native_size
        end;
        v8.update = function(p22, p23, _) --[[ Name: update ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_2, (ref 4): v_u_12, (copy 5): p_u_6 ]]
            local v24, v25
            if v_u_10 == true then
                v24 = 1.1
                v25 = math.sin(v_u_11) * 1.25
                v_u_11 = v_u_2:IncrementWrap(v_u_11, 0.05 * p23, 6.283185307179586)
            else
                v24 = 1
                v25 = 0
            end;
            local v26 = v24 + v_u_12
            v_u_12 = v_u_2:Expt(v_u_12, 0, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p23)
            p_u_6:set_scale(v_u_2:Expt(p_u_6:get_scale(), v26, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p23))
            p_u_6:set_rotation_z(v_u_2:Expt(p_u_6:get_rotation().Z, v25, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p23))
            p22:layout()
        end;
        local v_u_27 = nil
        v8.set_song_info = function(p28, p29, p30) --[[ Name: set_song_info ]] --[[ Line: 87 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_4, (ref 3): v_u_15, (ref 4): v_u_16, (ref 5): v_u_5, (ref 6): v_u_17, (ref 7): v_u_18, (ref 8): v_u_19 ]]
            v_u_27 = p29
            v_u_4:singleton():render_coverimage_for_key(v_u_15, v_u_16, p29)
            v_u_5:render_songkey_color_icons(p29, v_u_17, v_u_18)
            v_u_19.Text = string.format("%d", p30)
            p28:set_alpha(1)
            p28:set_enabled(true)
        end;
        v8.set_song_info_empty = function(p31) --[[ Name: set_song_info_empty ]] --[[ Line: 100 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            v_u_27 = nil
            p31:set_alpha(0)
            p31:set_enabled(false)
        end;
        v8.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27;
        end;
        local v_u_32 = true
        v8.set_enabled = function(p33, p34) --[[ Name: set_enabled ]] --[[ Line: 111 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_32 ]]
            if p34 == false then
                v_u_10 = false
            end;
            v_u_32 = p34
            return p33;
        end;
        v8.set_visible = function(p35, p36) --[[ Name: set_visible ]] --[[ Line: 119 ]]
            --[[ Upvalues: (copy 1): v_u_9 ]]
            if p36 == true then
                v_u_9.SurfaceGui.Enabled = true
            else
                v_u_9.SurfaceGui.Enabled = false
            end;
            p35:set_enabled(p36)
            return p35;
        end;
        local v_u_37 = false
        v8.set_inventory_selected = function(p38, p39) --[[ Name: set_inventory_selected ]] --[[ Line: 130 ]]
            --[[ Upvalues: (ref 1): v_u_37, (copy 2): p_u_6 ]]
            v_u_37 = p39
            p38:set_alpha(p38:get_alpha(), true)
            if v_u_37 then
                p_u_6:get_child_part().SurfaceGui.ZOffset = 1500 + p_u_6:get_child_id()
            else
                p_u_6:get_child_part().SurfaceGui.ZOffset = 1000 + p_u_6:get_child_id()
            end;
        end;
        v8.set_position = function(_, p40) --[[ Name: set_position ]] --[[ Line: 140 ]]
            --[[ Upvalues: (copy 1): v_u_9, (copy 2): p_u_6 ]]
            v_u_9.Position = p40
            p_u_6:update_basis_offset()
        end;
        v8.is_selectable = function(_) --[[ Name: is_selectable ]] --[[ Line: 145 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            return v_u_32;
        end;
        v8.get_selected = function(_) --[[ Name: get_selected ]] --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10;
        end;
        v8.trigger_element = function(_, _) --[[ Name: trigger_element ]] --[[ Line: 153 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_12 ]]
            p_u_7()
            v_u_12 = v_u_12 + 0.25
        end;
        v8.set_selected = function(_, _, p41) --[[ Name: set_selected ]] --[[ Line: 158 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            v_u_10 = p41
        end;
        v8.get_native_size = function(p42) --[[ Name: get_native_size ]] --[[ Line: 162 ]]
            return p42._native_size;
        end;
        v8.get_size = function(p43) --[[ Name: get_size ]] --[[ Line: 165 ]]
            return p43._size;
        end;
        v8.set_size = function(p44, p45) --[[ Name: set_size ]] --[[ Line: 168 ]]
            --[[ Upvalues: (copy 1): v_u_9 ]]
            p44._size = p45
            v_u_9.Size = Vector3.new(p45.X, p45.Y, 0)
        end;
        v8.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 172 ]]
            --[[ Upvalues: (copy 1): v_u_9 ]]
            return v_u_9.Position;
        end;
        local v_u_46 = 1
        v8.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 177 ]]
            --[[ Upvalues: (ref 1): v_u_46 ]]
            return v_u_46;
        end;
        v8.set_alpha = function(_, p47, p48) --[[ Name: set_alpha ]] --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_46, (ref 2): v_u_37, (ref 3): v_u_19, (ref 4): v_u_13, (ref 5): v_u_1, (ref 6): v_u_14, (ref 7): v_u_15, (ref 8): v_u_16, (ref 9): v_u_17, (ref 10): v_u_18 ]]
            if p47 ~= v_u_46 or p48 == true then
                v_u_46 = p47
                local v49 = 0
                local v50 = 0
                if v_u_37 then
                    v50 = v_u_46
                    v_u_19.TextColor3 = Color3.new(0, 0, 0)
                else
                    v49 = v_u_46
                    v_u_19.TextColor3 = Color3.new(1, 1, 1)
                end;
                v_u_13.ImageTransparency = v_u_1:tra(v49)
                v_u_13.Name = v_u_1:r_set_alpha_generate_name({
                    ["ImageAlpha"] = v49
                }, "Pane")
                v_u_14.ImageTransparency = v_u_1:tra(v50)
                v_u_14.Name = v_u_1:r_set_alpha_generate_name({
                    ["ImageAlpha"] = v50
                }, "PaneSelected")
                v_u_15.ImageTransparency = v_u_1:tra(v_u_46)
                v_u_15.Name = v_u_1:r_set_alpha_generate_name({
                    ["ImageAlpha"] = v_u_46
                }, "AlbumArt")
                v_u_16.ImageTransparency = v_u_1:tra(v_u_46)
                v_u_16.Name = v_u_1:r_set_alpha_generate_name({
                    ["ImageAlpha"] = v_u_46
                }, "AlbumArtOverlay")
                v_u_17.ImageTransparency = v_u_1:tra(v_u_46)
                v_u_17.Name = v_u_1:r_set_alpha_generate_name({
                    ["ImageAlpha"] = v_u_46
                }, "PrimaryColorIcon")
                v_u_18.ImageTransparency = v_u_1:tra(v_u_46)
                v_u_18.Name = v_u_1:r_set_alpha_generate_name({
                    ["ImageAlpha"] = v_u_46
                }, "SecondaryColorIcon")
                v_u_19.TextTransparency = v_u_1:tra(v_u_46)
                v_u_19.Name = v_u_1:r_set_alpha_generate_name({
                    ["TextAlpha"] = v_u_46
                }, "CopiesDisplay")
            end;
        end;
        v8:cons()
        return v8;
    end
};
