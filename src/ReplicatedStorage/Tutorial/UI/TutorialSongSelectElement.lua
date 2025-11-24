-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Menu.CycleElementBase)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
return {
    ["new"] = function(_, p_u_5, _, p_u_6) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_1 ]]
        local v7 = v_u_3:new()
        local v_u_8 = p_u_5:get_child_part()
        local v_u_9 = false
        local v_u_10 = 0
        local v_u_11 = 0
        local v_u_12 = nil
        local v_u_13 = nil
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        v7.cons = function(p18) --[[ Name: cons ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_5, (ref 3): v_u_13, (ref 4): v_u_14, (ref 5): v_u_15, (ref 6): v_u_16, (ref 7): v_u_17 ]]
            v_u_12 = p_u_5:get_child_part().SurfaceGui.Frame.Pane
            v_u_13 = p_u_5:get_child_part().SurfaceGui.Frame.PaneSelected
            v_u_14 = p_u_5:get_child_part().SurfaceGui.Frame.Pane.AlbumArt
            v_u_15 = p_u_5:get_child_part().SurfaceGui.Frame.Pane.AlbumArtOverlay
            v_u_16 = p_u_5:get_child_part().SurfaceGui.Frame.TitleDisplay
            v_u_17 = p_u_5:get_child_part().SurfaceGui.Frame.ArtistDisplay
            p18:set_alpha(1)
            p18:layout()
        end;
        v7.layout = function(p19) --[[ Name: layout ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): p_u_5, (copy 2): v_u_8 ]]
            p_u_5:layout()
            p19._native_size = v_u_8.Size
            p19._size = p19._native_size
        end;
        v7.update = function(p20, p21, _) --[[ Name: update ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_2, (ref 4): v_u_11, (copy 5): p_u_5 ]]
            local v22, v23
            if v_u_9 == true then
                v22 = 1.1
                v23 = math.sin(v_u_10) * 1.25
                v_u_10 = v_u_2:IncrementWrap(v_u_10, 0.05 * p21, 6.283185307179586)
            else
                v22 = 1
                v23 = 0
            end;
            local v24 = v22 + v_u_11
            v_u_11 = v_u_2:Expt(v_u_11, 0, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p21)
            p_u_5:set_scale(v_u_2:Expt(p_u_5:get_scale(), v24, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p21))
            p_u_5:set_rotation_z(v_u_2:Expt(p_u_5:get_rotation().Z, v23, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p21))
            p20:layout()
        end;
        local v_u_25 = nil
        v7.set_song_key = function(_, p26) --[[ Name: set_song_key ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_16, (ref 3): v_u_4, (ref 4): v_u_17, (ref 5): v_u_14, (ref 6): v_u_15 ]]
            v_u_25 = p26
            v_u_16.Text = v_u_4:singleton():get_title_for_key(p26)
            v_u_17.Text = v_u_4:singleton():get_artist_for_key(p26)
            v_u_4:singleton():render_coverimage_for_key(v_u_14, v_u_15, p26)
        end;
        v7.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            return v_u_25;
        end;
        local v_u_27 = true
        v7.set_enabled = function(p28, p29) --[[ Name: set_enabled ]] --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            if p29 == false then
                v_u_9 = false
            end;
            v_u_27 = p29
            return p28;
        end;
        v7.set_visible = function(p30, p31) --[[ Name: set_visible ]] --[[ Line: 109 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            if p31 == true then
                v_u_8.SurfaceGui.Enabled = true
            else
                v_u_8.SurfaceGui.Enabled = false
            end;
            p30:set_enabled(p31)
            return p30;
        end;
        v7.set_position = function(_, p32) --[[ Name: set_position ]] --[[ Line: 119 ]]
            --[[ Upvalues: (copy 1): v_u_8, (copy 2): p_u_5 ]]
            v_u_8.Position = p32
            p_u_5:update_basis_offset()
        end;
        local v_u_33 = false
        v7.set_item_selected = function(p34, p35) --[[ Name: set_item_selected ]] --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            v_u_33 = p35
            p34:set_alpha(p34:get_alpha(), true)
            return p34;
        end;
        v7.get_item_selected = function(_) --[[ Name: get_item_selected ]] --[[ Line: 131 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            return v_u_33;
        end;
        v7.is_selectable = function(_) --[[ Name: is_selectable ]] --[[ Line: 133 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27;
        end;
        v7.get_selected = function(_) --[[ Name: get_selected ]] --[[ Line: 137 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end;
        v7.trigger_element = function(_, _) --[[ Name: trigger_element ]] --[[ Line: 141 ]]
            --[[ Upvalues: (copy 1): p_u_6, (ref 2): v_u_33, (ref 3): v_u_11 ]]
            p_u_6()
            if v_u_33 == true then
                v_u_11 = v_u_11 + 0.25
            else
                v_u_11 = v_u_11 - 0.25
            end;
        end;
        v7.set_selected = function(p36, _, p37) --[[ Name: set_selected ]] --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_5 ]]
            v_u_9 = p37
            if v_u_9 == true then
                p_u_5:get_child_part().SurfaceGui.ZOffset = 2000 + p_u_5:get_child_id()
            else
                p_u_5:get_child_part().SurfaceGui.ZOffset = 1250 + p_u_5:get_child_id()
            end;
            p36:set_alpha(p36:get_alpha(), true)
        end;
        v7.get_native_size = function(p38) --[[ Name: get_native_size ]] --[[ Line: 160 ]]
            return p38._native_size;
        end;
        v7.get_size = function(p39) --[[ Name: get_size ]] --[[ Line: 163 ]]
            return p39._size;
        end;
        v7.set_size = function(p40, p41) --[[ Name: set_size ]] --[[ Line: 166 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            p40._size = p41
            v_u_8.Size = Vector3.new(p41.X, p41.Y, 0.2)
        end;
        v7.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 170 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            return v_u_8.Position;
        end;
        local v_u_42 = 1
        v7.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 175 ]]
            --[[ Upvalues: (ref 1): v_u_42 ]]
            return v_u_42;
        end;
        v7.set_alpha = function(_, p43, p44) --[[ Name: set_alpha ]] --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_9, (ref 3): v_u_33, (ref 4): v_u_12, (ref 5): v_u_1, (ref 6): v_u_13, (ref 7): v_u_17, (ref 8): v_u_16, (ref 9): v_u_14, (ref 10): v_u_15 ]]
            if p43 ~= v_u_42 or p44 == true then
                v_u_42 = p43
                local v45 = 0
                local v46 = 0
                local v47 = 0
                if v_u_9 == true then
                    v46 = v_u_42 * 0.85
                    v47 = v_u_42
                else
                    v45 = v_u_42 * 0.85
                end;
                if v_u_33 == true then
                    v_u_12.BackgroundColor3 = v_u_1:color3(244, 240, 255)
                    v_u_13.BackgroundColor3 = v_u_12.BackgroundColor3
                    v_u_17.TextColor3 = v_u_1:color3(0, 0, 0)
                    v_u_16.TextColor3 = v_u_1:color3(188, 156, 24)
                else
                    v_u_12.BackgroundColor3 = v_u_1:color3(13, 0, 79)
                    v_u_17.TextColor3 = v_u_1:color3(255, 255, 255)
                    v_u_16.TextColor3 = v_u_1:color3(241, 200, 30)
                    v_u_13.BackgroundColor3 = v_u_12.BackgroundColor3
                end;
                v_u_12.BackgroundTransparency = v_u_1:tra(v45)
                v_u_12.Name = v_u_1:r_set_alpha_generate_name({
                    ["BackgroundAlpha"] = v45
                }, "Pane")
                v_u_13.BackgroundTransparency = v_u_1:tra(v46)
                v_u_13.Name = v_u_1:r_set_alpha_generate_name({
                    ["BackgroundAlpha"] = v46
                }, "PaneSelected")
                v_u_14.ImageTransparency = v_u_1:tra(v_u_42)
                v_u_14.Name = v_u_1:r_set_alpha_generate_name({
                    ["ImageAlpha"] = v_u_42
                }, "AlbumArt")
                v_u_15.ImageTransparency = v_u_1:tra(v_u_42)
                v_u_15.Name = v_u_1:r_set_alpha_generate_name({
                    ["ImageAlpha"] = v_u_42
                }, "AlbumArtOverlay")
                v_u_16.TextTransparency = v_u_1:tra(v47)
                v_u_16.Name = v_u_1:r_set_alpha_generate_name({
                    ["TextAlpha"] = v47
                }, "TitleDisplay")
                v_u_17.TextTransparency = v_u_1:tra(v47)
                v_u_17.Name = v_u_1:r_set_alpha_generate_name({
                    ["TextAlpha"] = v47
                }, "ArtistDisplay")
            end;
        end;
        v7:cons()
        return v7;
    end
};
