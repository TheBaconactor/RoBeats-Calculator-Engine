-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:38 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Local.GameJoinProtocol)
local v_u_9 = require(game.ReplicatedStorage.Lobby.UI.GameStartV2PlayerDisplay)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_12 = require(game.ReplicatedStorage.AudioData.SelectableArtists)
local v_u_13 = {
    ["Mode"] = {
        ["WaitingForLoad"] = 0,
        ["WaitingForClientDoStart"] = 1,
        ["ClientDoStart"] = 2,
        ["WasPreloadBooted"] = 3
    }
}
v_u_13.new = function(_, p_u_14, p_u_15, p_u_16, p_u_17) --[[ Name: new ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_13, (copy 3): v_u_8, (copy 4): v_u_5, (copy 5): v_u_2, (copy 6): v_u_10, (copy 7): v_u_1, (copy 8): v_u_7, (copy 9): v_u_12, (copy 10): v_u_11, (copy 11): v_u_9, (copy 12): v_u_6, (copy 13): v_u_4 ]]
    local v18 = v_u_3:new(p_u_15, p_u_16)
    local v_u_19 = nil
    local l_WaitingForLoad_0 = v_u_13.Mode.WaitingForLoad
    local v_u_20 = 1
    local v_u_21 = 0
    local l_ExtraLoadTimeMS_0 = v_u_8.ExtraLoadTimeMS
    if l_ExtraLoadTimeMS_0 > 0 then
        v_u_5:puts("debug_extra_load_time(%.2f)", l_ExtraLoadTimeMS_0)
    end;
    local v_u_22 = false
    local v_u_23 = v_u_2:new()
    local v_u_24 = 1
    local v_u_25 = 0
    v18.cons = function(p26) --[[ Name: cons ]] --[[ Line: 48 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_14, (copy 3): p_u_17, (ref 4): v_u_19, (ref 5): v_u_1, (ref 6): v_u_7, (ref 7): v_u_12, (ref 8): v_u_11 ]]
        v_u_10:should_load_textures(false)
        p_u_14._chat:store_chat_visible()
        p_u_14._chat:set_chat_visible(false)
        p_u_17:begin_preload()
        if p_u_14._player_blob_manager:is_synced() == false then
            p_u_14._player_blob_manager:do_sync()
        end;
        v_u_19 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.GameStartV2UI:Clone()
        v_u_19.Name = v_u_1:gen_name(v_u_19.Name)
        v_u_19.Parent = v_u_10:get_world_ui_folder()
        p26._native_size = v_u_19.PrimaryPart.Size
        p26._size = p26._native_size
        local l_Frame_0 = v_u_19.MainSurface.SurfaceGui.Frame
        l_Frame_0.SongTitleDisplay.Text = v_u_7:singleton():get_title_for_key(p_u_17:get_selected_song_key())
        l_Frame_0.ArtistDisplay.Text = v_u_7:singleton():get_artist_for_key(p_u_17:get_selected_song_key())
        l_Frame_0.SongDifficultySection.Display.Text = v_u_7:singleton():get_difficulty_for_key(p_u_17:get_selected_song_key())
        l_Frame_0.SongDifficultySection.Display.TextColor3 = v_u_7:singleton():get_difficulty_color_for_key(p_u_17:get_selected_song_key())
        local v27 = false
        local v28, v29 = v_u_12:artist_name_is_selectable(v_u_7:singleton():get_artist_for_key(p_u_17:get_selected_song_key()))
        if v28 then
            local v30 = v_u_12:artist_name_to_icon(v29)
            if #v30 > 0 then
                l_Frame_0.ArtistIcon.Image = v30
                v27 = true
            end;
        end;
        if v27 == false then
            l_Frame_0.ArtistIcon.Image = v_u_1:transparent_assetid()
        end;
        v_u_7:singleton():render_coverimage_for_key(l_Frame_0.SongPanel.AlbumArt, l_Frame_0.SongPanel.AlbumArtOverlay, p_u_17:get_selected_song_key())
        v_u_11:render_songkey_colorsection(p_u_17:get_selected_song_key(), l_Frame_0.SongPanel.ColorSection)
        l_Frame_0.DescriptionBack.TextLabel.Text = v_u_7:singleton():get_description_for_key(p_u_17:get_selected_song_key())
        p26:create_elements()
        p26:layout()
    end;
    v18.create_elements = function(p31) --[[ Name: create_elements ]] --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_19, (ref 3): v_u_9, (copy 4): v_u_23 ]]
        local v32 = v_u_2:new():push_back_table_list({
            v_u_19.Anchors.Slot1,
            v_u_19.Anchors.Slot2,
            v_u_19.Anchors.Slot3,
            v_u_19.Anchors.Slot4
        })
        local v33 = v_u_2:new():push_back_table_list({
            v_u_19.PlayerSlotIconProto,
            v_u_19.PlayerSlotIconProto:Clone(),
            v_u_19.PlayerSlotIconProto:Clone(),
            v_u_19.PlayerSlotIconProto:Clone()
        })
        for v34 = 1, 4 do
            local v35 = v_u_9:new(v33:get(v34), p31, v_u_19.PrimaryPart)
            v35:set_position(v32:get(v34).Slot.Position)
            v35:set_loaded(false)
            v_u_23:push_back(v35)
        end;
    end;
    v18.behaviour_update = function(p36, p37, p38) --[[ Name: behaviour_update ]] --[[ Line: 126 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_6, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_4, (copy 6): v_u_23, (ref 7): v_u_5, (ref 8): l_WaitingForLoad_0, (ref 9): v_u_13, (ref 10): v_u_22, (copy 11): p_u_16, (ref 12): v_u_25, (copy 13): p_u_14, (ref 14): l_ExtraLoadTimeMS_0 ]]
        p36:behaviour_update_base(p37, p38)
        p_u_17:update(p37)
        if p36._current_mode == v_u_6.MODE_OPEN then
            if v_u_20 < 4 then
                v_u_21 = v_u_21 + v_u_4:sec_to_tick(0.15) * p37
                if v_u_21 >= 1 then
                    v_u_20 = v_u_20 + 1
                    v_u_21 = 0
                end;
            end;
            local v39 = p_u_17:get_slots()
            for v40 = 1, v_u_23:count() do
                local v41 = v_u_23:get(v40)
                if v39:contains(v40) and v40 <= v_u_20 then
                    local v42 = v39:get(v40)
                    v41:set_game_instance_player(v42)
                    v41:sub_display_loaded_or_timeout(v42)
                    v41:set_loaded(true)
                else
                    v41:set_loaded(false)
                end;
            end;
            if p_u_17:was_preload_booted() then
                v_u_5:puts("GameStartUI WAS_PRELOAD_BOOTED")
                l_WaitingForLoad_0 = v_u_13.Mode.WasPreloadBooted
                v_u_22 = true
                p_u_16:remove_all_menus()
            elseif l_WaitingForLoad_0 == v_u_13.Mode.WaitingForLoad then
                local v43 = p_u_17:is_preload_finished()
                if v43 == false then
                    v_u_25 = v_u_25 + v_u_4:TimescaleToDeltaTime(p37)
                    if v_u_25 > 8 then
                        p_u_17:trigger_load_retry()
                        v_u_25 = 0
                    end;
                end;
                if v_u_20 >= 4 and (v43 and p_u_14._player_blob_manager:is_synced()) then
                    if l_ExtraLoadTimeMS_0 > 0 then
                        l_ExtraLoadTimeMS_0 = l_ExtraLoadTimeMS_0 - v_u_4:TimescaleToDeltaTime(p37) * 1000
                        return;
                    end;
                    p_u_17:fire_preload_finished()
                    l_WaitingForLoad_0 = v_u_13.Mode.WaitingForClientDoStart
                end;
                if p_u_17:notify_client_do_start() then
                    l_WaitingForLoad_0 = v_u_13.Mode.WaitingForClientDoStart
                    return;
                end;
            elseif l_WaitingForLoad_0 == v_u_13.Mode.WaitingForClientDoStart and p_u_17:notify_client_do_start() then
                p_u_16:remove_all_menus()
                l_WaitingForLoad_0 = v_u_13.Mode.ClientDoStart
            end;
        else
            return;
        end;
    end;
    v18.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 196 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_22, (ref 3): v_u_5, (copy 4): p_u_17 ]]
        v_u_19:Destroy()
        if v_u_22 then
            v_u_5:warnf("GameStartV2UI _was_preload_booted")
        end;
        p_u_17:client_do_start()
    end;
    v18.layout = function(p44) --[[ Name: layout ]] --[[ Line: 205 ]]
        --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_24, (ref 3): v_u_19 ]]
        p_u_15:uiobj_rescale_to_max_nxy(p44, 0.65, 0.65, v_u_24)
        v_u_19:SetPrimaryPartCFrame(p_u_15:get_cframe({
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p44:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
    end;
    v18.visual_update = function(p45, p46, p47) --[[ Name: visual_update ]] --[[ Line: 214 ]]
        --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_24 ]]
        p45:visual_update_base(p46, p47)
        for v48 = 1, v_u_23:count() do
            local v49 = v_u_23:get(v48)
            v49:set_scale(v_u_24)
            v49:visual_update(p46, p47)
        end;
    end;
    local v_u_50 = -1
    v18.set_alpha = function(_, p51) --[[ Name: set_alpha ]] --[[ Line: 225 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_1, (ref 3): v_u_19 ]]
        if v_u_50 ~= p51 then
            v_u_50 = p51
            v_u_1:r_set_alpha(v_u_19, v_u_50)
        end;
    end;
    v18.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 230 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        return v_u_50;
    end;
    v18.set_scale = function(_, p52) --[[ Name: set_scale ]] --[[ Line: 231 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24 = p52
    end;
    v18.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 232 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24;
    end;
    v18.get_native_size = function(p53) --[[ Name: get_native_size ]] --[[ Line: 234 ]]
        return p53._native_size;
    end;
    v18.get_size = function(p54) --[[ Name: get_size ]] --[[ Line: 237 ]]
        return p54._size;
    end;
    v18.set_size = function(p55, p56) --[[ Name: set_size ]] --[[ Line: 240 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        p55._size = p56
        if v_u_19 ~= nil and v_u_19.PrimaryPart ~= nil then
            v_u_19.PrimaryPart.Size = Vector3.new(p56.X, p56.Y, 0)
        end;
    end;
    v18.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 246 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        return v_u_19.PrimaryPart.Position;
    end;
    v18.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 249 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        return v_u_19.PrimaryPart.SurfaceGui;
    end;
    v18:cons()
    return v18;
end;
return v_u_13;
