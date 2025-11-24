-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_10 = require(game.ReplicatedStorage.Menu.CharacterDialogue)
return {
    ["new"] = function(_, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_9, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_8, (copy 8): v_u_6, (copy 9): v_u_10, (copy 10): v_u_7 ]]
        local v16 = v_u_3:new(p_u_12, p_u_13)
        local v_u_17 = nil
        local v_u_18 = 1
        local v_u_19 = 1
        local v_u_20 = v_u_2:new()
        local v_u_21 = nil
        local v_u_22 = 0
        local v_u_23 = 0
        local v_u_24 = nil
        local v_u_25 = 0
        local v_u_26 = 0
        local v_u_27 = nil
        local v_u_28 = nil
        v16.cons = function(p_u_29) --[[ Name: cons ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1, (ref 3): v_u_9, (copy 4): p_u_11, (ref 5): v_u_5, (ref 6): v_u_4, (copy 7): p_u_12, (ref 8): v_u_8, (copy 9): p_u_13, (ref 10): v_u_21, (ref 11): v_u_24, (copy 12): v_u_20, (ref 13): v_u_6, (copy 14): p_u_14, (ref 15): v_u_28, (ref 16): v_u_10, (copy 17): p_u_15, (ref 18): v_u_27 ]]
            v_u_17 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.TutorialSongAcquiredUI:Clone()
            v_u_17.Name = v_u_1:gen_name(v_u_17.Name)
            v_u_17.Parent = v_u_9:get_world_ui_folder()
            p_u_29._native_size = v_u_17.PrimaryPart.Size
            p_u_29._size = p_u_29._native_size
            p_u_29:add_cycle_element(p_u_11, 1, v_u_5:new(v_u_4:new(p_u_29, v_u_17.PrimaryPart, v_u_17.BackButtonSurface), p_u_12, function() --[[ Line: 51 ]]
                --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_8, (ref 3): p_u_13, (copy 4): p_u_29 ]]
                p_u_11._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
                p_u_13:remove_menu(p_u_29)
            end))
            v_u_21 = v_u_4:new(p_u_29, v_u_17.PrimaryPart, v_u_17.TitleSurface)
            v_u_24 = v_u_4:new(p_u_29, v_u_17.PrimaryPart, v_u_17.ShineSurface)
            v_u_20:push_back(v_u_4:new(p_u_29, v_u_17.PrimaryPart, v_u_17.AlbumArtSurface))
            v_u_20:push_back(v_u_4:new(p_u_29, v_u_17.PrimaryPart, v_u_17.WaveformSurface))
            v_u_20:push_back(v_u_21)
            v_u_20:push_back(v_u_24)
            v_u_6:singleton():render_coverimage_for_key(v_u_17.AlbumArtSurface.SurfaceGui.Frame.CoverSection.AlbumArt, v_u_17.AlbumArtSurface.SurfaceGui.Frame.CoverSection.AlbumArtOverlay, p_u_14)
            v_u_17.AlbumArtSurface.SurfaceGui.Frame.TitleDisplay.TextLabel.Text = v_u_6:singleton():get_title_for_key(p_u_14)
            v_u_17.AlbumArtSurface.SurfaceGui.Frame.ArtistDisplay.TextLabel.Text = v_u_6:singleton():get_artist_for_key(p_u_14)
            v_u_17.AlbumArtSurface.SurfaceGui.Frame.TitleDisplay.Name = v_u_1:r_set_alpha_generate_name({
                ["BackgroundAlpha"] = 0.5
            }, "TitleDisplay")
            v_u_17.AlbumArtSurface.SurfaceGui.Frame.ArtistDisplay.Name = v_u_1:r_set_alpha_generate_name({
                ["BackgroundAlpha"] = 0.5
            }, "ArtistDisplay")
            v_u_28 = v_u_10:new("Starlet", v_u_17.StarletDialogue, v_u_4:new(p_u_29, v_u_17.PrimaryPart, v_u_17.StarletDialogue))
            if p_u_15 == true then
                v_u_28:display_text("Know how to play already, eh? Well... Take this song. Should be a piece of cake for you!")
            else
                p_u_11._sfx_manager:play_sfx(v_u_8.SFX_ENDCHEER_1)
                v_u_28:display_text("Nice work! Take this song. Now you can play it whenever you want!")
            end;
            v_u_27 = p_u_29:add_cycle_element(p_u_11, 1, v_u_5:new(v_u_4:new(p_u_29, v_u_17.PrimaryPart, v_u_17.Starlet), p_u_11._spui, function() --[[ Line: 91 ]]
                --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_8, (ref 3): p_u_15, (ref 4): v_u_28 ]]
                p_u_11._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                if p_u_15 == true then
                    v_u_28:display_text("You got some guts, that\'s for sure!")
                else
                    v_u_28:display_text("What\'d you think of the song? Some tough parts in there, that\'s for sure!")
                end;
            end):set_selected_tar_scale(1.05):set_triggered_scale_offset(0.1))
            p_u_11._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
            p_u_29:layout()
        end;
        v16.behaviour_update = function(p30, p31, _) --[[ Name: behaviour_update ]] --[[ Line: 107 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_28, (ref 3): v_u_22, (ref 4): v_u_7, (ref 5): v_u_23, (ref 6): v_u_21, (ref 7): v_u_26, (ref 8): v_u_25, (ref 9): v_u_24 ]]
            p30:behaviour_update_base(p31, p_u_11)
            v_u_28:update(p31)
            v_u_22 = v_u_7:incr_wrap(v_u_22, v_u_7:sec_to_tick(1.23) * p31, 1)
            v_u_23 = v_u_7:incr_wrap(v_u_23, v_u_7:sec_to_tick(1.02) * p31, 1)
            v_u_21:set_scale(math.sin(v_u_22 * 3.141592653589793 * 2) * 0.1 + 1)
            v_u_21:set_rotation_z(math.sin(v_u_23 * 3.141592653589793 * 2) * 5)
            v_u_26 = v_u_7:incr_wrap(v_u_26, v_u_7:sec_to_tick(2.12) * p31, 1)
            v_u_25 = v_u_7:incr_wrap(v_u_25, v_u_7:sec_to_tick(20) * p31, 1)
            v_u_24:set_scale(math.sin(v_u_26 * 3.141592653589793 * 2) * 0.05 + 1)
            v_u_24:set_rotation_z(v_u_25 * 360)
        end;
        v16.layout = function(p32) --[[ Name: layout ]] --[[ Line: 124 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_19, (ref 3): v_u_17, (ref 4): v_u_28, (copy 5): v_u_20 ]]
            p_u_12:uiobj_rescale_to_max_nxy(p32, 0.7, 0.8, v_u_19)
            v_u_17:SetPrimaryPartCFrame(p_u_12:get_cframe({
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p32:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            }))
            v_u_28:layout()
            for v33 = 1, v_u_20:count() do
                v_u_20:get(v33):layout()
            end;
        end;
        v16.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 138 ]]
            --[[ Upvalues: (ref 1): v_u_17, (copy 2): p_u_11 ]]
            v_u_17:Destroy()
            p_u_11._tutorial_manager:tutorial_after_song_acquire()
        end;
        v16.set_alpha = function(_, p34) --[[ Name: set_alpha ]] --[[ Line: 143 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_1, (ref 3): v_u_17 ]]
            if v_u_18 ~= p34 then
                v_u_18 = p34
                v_u_1:r_set_alpha(v_u_17, v_u_18)
            end;
        end;
        v16.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        v16.set_scale = function(_, p35) --[[ Name: set_scale ]] --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            v_u_19 = p35
        end;
        v16.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 151 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19;
        end;
        v16.get_native_size = function(p36) --[[ Name: get_native_size ]] --[[ Line: 153 ]]
            return p36._native_size;
        end;
        v16.get_size = function(p37) --[[ Name: get_size ]] --[[ Line: 156 ]]
            return p37._size;
        end;
        v16.set_size = function(p38, p39) --[[ Name: set_size ]] --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            p38._size = p39
            v_u_17.PrimaryPart.Size = Vector3.new(p39.X, p39.Y, 0)
        end;
        v16.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 163 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.Position;
        end;
        v16.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 166 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.SurfaceGui;
        end;
        v16:cons()
        return v16;
    end
};
