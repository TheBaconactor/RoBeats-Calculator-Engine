-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:39 PM
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
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.SongPreviewUIButton)
local v_u_12 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
return {
    ["new"] = function(_, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_10, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_6, (copy 8): v_u_12, (copy 9): v_u_8, (copy 10): v_u_9, (copy 11): v_u_11, (copy 12): v_u_7 ]]
        local v18 = v_u_3:new(p_u_14, p_u_15)
        local v_u_19 = nil
        local v_u_20 = 1
        local v_u_21 = 1
        local v_u_22 = v_u_2:new()
        local v_u_23 = nil
        local v_u_24 = 0
        local v_u_25 = 0
        local v_u_26 = nil
        local v_u_27 = 0
        local v_u_28 = 0
        local v_u_29 = nil
        local v_u_30 = nil
        v18.cons = function(p_u_31) --[[ Name: cons ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_1, (ref 3): v_u_10, (ref 4): v_u_30, (copy 5): p_u_13, (copy 6): p_u_16, (ref 7): v_u_5, (ref 8): v_u_4, (copy 9): p_u_14, (copy 10): p_u_15, (ref 11): v_u_23, (ref 12): v_u_26, (copy 13): v_u_22, (ref 14): v_u_6, (ref 15): v_u_12, (ref 16): v_u_8, (ref 17): v_u_9, (ref 18): v_u_29, (ref 19): v_u_11 ]]
            v_u_19 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.SongAcquiredV2UI:Clone()
            v_u_19.Name = v_u_1:gen_name(v_u_19.Name)
            v_u_19.Parent = v_u_10:get_world_ui_folder()
            p_u_31._native_size = v_u_19.PrimaryPart.Size
            p_u_31._size = p_u_31._native_size
            p_u_31:layout()
            v_u_30 = p_u_13._bgm_manager:begin_preview_songkey(p_u_16)
            p_u_31:add_cycle_element(p_u_13, 1, v_u_5:new(v_u_4:new(p_u_31, v_u_19.PrimaryPart, v_u_19.BackButtonSurface), p_u_14, function() --[[ Line: 55 ]]
                --[[ Upvalues: (ref 1): p_u_15, (copy 2): p_u_31 ]]
                p_u_15:remove_menu(p_u_31)
            end))
            v_u_23 = v_u_4:new(p_u_31, v_u_19.PrimaryPart, v_u_19.TitleSurface)
            v_u_26 = v_u_4:new(p_u_31, v_u_19.PrimaryPart, v_u_19.ShineSurface)
            v_u_22:push_back(v_u_4:new(p_u_31, v_u_19.PrimaryPart, v_u_19.AlbumArtSurface))
            v_u_22:push_back(v_u_4:new(p_u_31, v_u_19.PrimaryPart, v_u_19.WaveformSurface))
            v_u_22:push_back(v_u_23)
            v_u_22:push_back(v_u_26)
            v_u_6:singleton():render_coverimage_for_key(v_u_19.AlbumArtSurface.SurfaceGui.Frame.CoverSection.AlbumArt, v_u_19.AlbumArtSurface.SurfaceGui.Frame.CoverSection.AlbumArtOverlay, p_u_16)
            v_u_12:render_songkey_colorsection(p_u_16, v_u_19.AlbumArtSurface.SurfaceGui.Frame.CoverSection.ColorSection)
            v_u_19.AlbumArtSurface.SurfaceGui.Frame.TitleDisplay.TextLabel.Text = v_u_6:singleton():get_title_for_key(p_u_16)
            v_u_19.AlbumArtSurface.SurfaceGui.Frame.ArtistDisplay.TextLabel.Text = v_u_6:singleton():get_artist_for_key(p_u_16)
            v_u_19.MainSurface.SurfaceGui.Frame.OwnedDisplay.Text = string.format("%d", v_u_8:get_song_key_owned_count(p_u_13._player_blob_manager:get_player_blob(), p_u_16))
            v_u_19.AlbumArtSurface.SurfaceGui.Frame.TitleDisplay.Name = v_u_1:r_set_alpha_generate_name({
                ["BackgroundAlpha"] = 0.5
            }, "TitleDisplay")
            v_u_19.AlbumArtSurface.SurfaceGui.Frame.ArtistDisplay.Name = v_u_1:r_set_alpha_generate_name({
                ["BackgroundAlpha"] = 0.5
            }, "ArtistDisplay")
            v_u_19.MainSurface.SurfaceGui.Frame.OwnedText.Back.Name = v_u_1:r_set_alpha_generate_name({
                ["BackgroundAlpha"] = 0.5
            }, "Back")
            p_u_13._sfx_manager:play_sfx(v_u_9.SFX_ACQUIRE)
            v_u_29 = p_u_31:add_cycle_element(p_u_13, 1, v_u_11:new(p_u_13, p_u_31, v_u_19.PrimaryPart, v_u_19.PlayPreviewButton))
            v_u_29:set_target_songkey(p_u_16)
        end;
        v18.behaviour_update = function(p32, p33, p34) --[[ Name: behaviour_update ]] --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_25, (ref 4): v_u_23, (ref 5): v_u_28, (ref 6): v_u_27, (ref 7): v_u_26 ]]
            p32:behaviour_update_base(p33, p34)
            v_u_24 = v_u_7:incr_wrap(v_u_24, v_u_7:sec_to_tick(1.23) * p33, 1)
            v_u_25 = v_u_7:incr_wrap(v_u_25, v_u_7:sec_to_tick(1.02) * p33, 1)
            v_u_23:set_scale(math.sin(v_u_24 * 3.141592653589793 * 2) * 0.1 + 1)
            v_u_23:set_rotation_z(math.sin(v_u_25 * 3.141592653589793 * 2) * 5)
            v_u_28 = v_u_7:incr_wrap(v_u_28, v_u_7:sec_to_tick(2.12) * p33, 1)
            v_u_27 = v_u_7:incr_wrap(v_u_27, v_u_7:sec_to_tick(20) * p33, 1)
            v_u_26:set_scale(math.sin(v_u_28 * 3.141592653589793 * 2) * 0.05 + 1)
            v_u_26:set_rotation_z(v_u_27 * 360)
        end;
        v18.layout = function(p35) --[[ Name: layout ]] --[[ Line: 107 ]]
            --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_21, (ref 3): v_u_19, (copy 4): v_u_22 ]]
            p_u_14:uiobj_rescale_to_max_nxy(p35, 0.9, 0.8, v_u_21)
            v_u_19:SetPrimaryPartCFrame(p_u_14:get_cframe({
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p35:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            }))
            for v36 = 1, v_u_22:count() do
                v_u_22:get(v36):layout()
            end;
        end;
        v18.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 120 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_30, (ref 3): v_u_19, (copy 4): p_u_17 ]]
            p_u_13._bgm_manager:stop_song_preview(v_u_30)
            v_u_19:Destroy()
            if p_u_17 ~= nil then
                p_u_17()
            end;
        end;
        v18.set_alpha = function(_, p37) --[[ Name: set_alpha ]] --[[ Line: 128 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_1, (ref 3): v_u_19 ]]
            if v_u_20 ~= p37 then
                v_u_20 = p37
                v_u_1:r_set_alpha(v_u_19, v_u_20)
            end;
        end;
        v18.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        v18.set_scale = function(_, p38) --[[ Name: set_scale ]] --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21 = p38
        end;
        v18.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 136 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21;
        end;
        v18.get_native_size = function(p39) --[[ Name: get_native_size ]] --[[ Line: 138 ]]
            return p39._native_size;
        end;
        v18.get_size = function(p40) --[[ Name: get_size ]] --[[ Line: 141 ]]
            return p40._size;
        end;
        v18.set_size = function(p41, p42) --[[ Name: set_size ]] --[[ Line: 144 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            p41._size = p42
            v_u_19.PrimaryPart.Size = Vector3.new(p42.X, p42.Y, 0)
        end;
        v18.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19.PrimaryPart.Position;
        end;
        v18.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 151 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19.PrimaryPart.SurfaceGui;
        end;
        v18:cons()
        return v18;
    end
};
