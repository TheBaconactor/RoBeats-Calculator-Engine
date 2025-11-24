-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:00 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPVector)
local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.SPImagePriority)
require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_7 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_8 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local s_ContentProvider_0 = game:GetService("ContentProvider")
return {
    ["new"] = function(_, p_u_9, p_u_10) --[[ Name: new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): s_ContentProvider_0, (copy 2): v_u_5, (copy 3): v_u_3, (copy 4): v_u_4, (copy 5): v_u_8, (copy 6): v_u_7, (copy 7): v_u_6, (copy 8): v_u_2, (copy 9): v_u_1 ]]
        local v11 = {}
        local l_RequestQueueSize_0 = s_ContentProvider_0.RequestQueueSize
        local function _() --[[ Name: update_remaining_assets_count ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): l_RequestQueueSize_0, (ref 2): s_ContentProvider_0 ]]
            l_RequestQueueSize_0 = s_ContentProvider_0.RequestQueueSize
        end;
        spawn(function() --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): l_RequestQueueSize_0, (ref 2): s_ContentProvider_0 ]]
            while true do
                while true do
                    l_RequestQueueSize_0 = s_ContentProvider_0.RequestQueueSize
                    if l_RequestQueueSize_0 <= 3 then
                        break;
                    end;
                    wait(0.2)
                end;
                wait(1)
            end;
        end)
        local v_u_12 = v_u_5:new()
        local v_u_13 = v_u_3:new()
        local l_ImageLabel_0 = Instance.new("ImageLabel")
        local v_u_14 = ""
        local v_u_15 = false
        local v_u_16 = 0
        v11.get_preload_game_asset_count = function(_) --[[ Name: get_preload_game_asset_count ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            return v_u_16;
        end;
        local l_ScreenGui_0 = Instance.new("ScreenGui")
        l_ScreenGui_0.Name = "SPImageLoader"
        l_ScreenGui_0.ResetOnSpawn = false
        l_ScreenGui_0.DisplayOrder = 0
        spawn(function() --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): l_ScreenGui_0 ]]
            l_ScreenGui_0.Parent = game.Players.LocalPlayer.PlayerGui
        end)
        local l_TextLabel_0 = Instance.new("TextLabel", l_ScreenGui_0)
        l_TextLabel_0.AnchorPoint = Vector2.new(0, 1)
        l_TextLabel_0.BackgroundTransparency = 1
        if v_u_4:is_console_ui() then
            l_TextLabel_0.Position = UDim2.new(0, 0, 0, v_u_4:topbar_size())
        else
            l_TextLabel_0.Position = UDim2.new(0, 0, 0, 0)
        end;
        l_TextLabel_0.Size = UDim2.new(1, 0, 0, 30)
        l_TextLabel_0.Font = Enum.Font.SourceSansBold
        l_TextLabel_0.Text = ""
        l_TextLabel_0.TextSize = 26
        l_TextLabel_0.TextColor3 = Color3.new(1, 1, 1)
        l_TextLabel_0.TextStrokeColor3 = Color3.new(0.2, 0.2, 0.2)
        l_TextLabel_0.TextStrokeTransparency = 0
        l_TextLabel_0.TextXAlignment = Enum.TextXAlignment.Center
        l_TextLabel_0.TextYAlignment = Enum.TextYAlignment.Top
        l_TextLabel_0.AutoLocalize = false
        local v_u_17 = -1
        local v_u_18 = true
        l_TextLabel_0.Visible = false
        local v_u_19 = v_u_8:invalid_songkey()
        local v_u_20 = v_u_19
        local v_u_21 = 0
        local function f_update_loading_display(p22, p23) --[[ Name: update_loading_display ]] --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_7, (ref 3): v_u_18, (ref 4): v_u_20, (copy 5): v_u_19, (ref 6): l_RequestQueueSize_0, (copy 7): l_TextLabel_0, (ref 8): v_u_8, (ref 9): v_u_17, (ref 10): v_u_4 ]]
            local v24 = false
            if p22._bgm_manager:is_preview_song_loading() then
                v_u_21 = v_u_21 + v_u_7:TimescaleToDeltaTime(p23)
                v24 = v_u_21 > 0.5 and true or v24
            else
                v_u_21 = 0
            end;
            if v24 then
                v_u_18 = true
            else
                v_u_20 = v_u_19
            end;
            if v_u_18 == false then
                if l_RequestQueueSize_0 > 10 then
                    v_u_18 = true
                end;
                return;
            elseif l_RequestQueueSize_0 <= 3 and not v24 then
                v_u_18 = false
                l_TextLabel_0.Visible = false
                return;
            elseif v24 == true then
                local v25 = p22._bgm_manager:get_preview_songkey()
                if v25 ~= v_u_20 and v_u_8:singleton():contains_key(v25) then
                    v_u_20 = v25
                    l_TextLabel_0.Text = string.format("Loading audio for \'%s\'...", v_u_8:singleton():get_title_for_key(v25))
                end;
                l_TextLabel_0.Visible = true
            elseif l_RequestQueueSize_0 ~= v_u_17 then
                v_u_17 = l_RequestQueueSize_0
                local v26 = l_RequestQueueSize_0
                if v26 == 1 then
                    l_TextLabel_0.Text = "Loading 1 asset..."
                else
                    l_TextLabel_0.Text = string.format("Loading %s assets...", v_u_4:comma_value(v26))
                end;
                l_TextLabel_0.Visible = true
            end;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 138 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_6, (ref 3): s_ContentProvider_0, (ref 4): v_u_16, (ref 5): v_u_2, (ref 6): v_u_1, (copy 7): v_u_12, (copy 8): p_u_9, (ref 9): v_u_4, (copy 10): v_u_13 ]]
            p_u_10:push_back(v_u_6.SurfaceAppearanceDecals)
            spawn(function() --[[ Line: 140 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): s_ContentProvider_0, (ref 3): v_u_16 ]]
                while p_u_10:count() > 0 do
                    local v27 = p_u_10:get(1)
                    if typeof(v27) == "table" then
                        s_ContentProvider_0:PreloadAsync(v27)
                        v_u_16 = v_u_16 + 1
                    else
                        s_ContentProvider_0:PreloadAsync({ v27 })
                    end;
                    p_u_10:pop_front()
                end;
            end)
            local v_u_28 = v_u_2:new()
            local v_u_29 = v_u_2:new()
            local function f_r_find_spdecals(p30) --[[ Name: r_find_spdecals ]] --[[ Line: 157 ]]
                --[[ Upvalues: (copy 1): f_r_find_spdecals, (ref 2): v_u_1, (ref 3): v_u_6, (copy 4): v_u_28, (copy 5): v_u_29, (ref 6): v_u_12 ]]
                for _, v31 in pairs(p30:GetChildren()) do
                    f_r_find_spdecals(v31)
                end;
                if p30.ClassName == "Decal" or (p30.ClassName == "Texture" or (p30.ClassName == "ImageLabel" or p30.ClassName == "MeshPart")) then
                    if (p30.ClassName == "Decal" or p30.ClassName == "Texture") and p30.Texture ~= "" then
                        return;
                    end;
                    if p30.ClassName == "ImageLabel" and p30.Image ~= "" then
                        return;
                    end;
                    if p30.ClassName == "MeshPart" and p30.TextureID ~= "" then
                        return;
                    end;
                    local v32 = p30:FindFirstChild("SPDecal")
                    if v32 ~= nil then
                        if v32.ClassName ~= "StringValue" then
                            v_u_1:errf("invalid spdecal at(%s)", p30:GetFullName())
                        end;
                        local l_Value_0 = v32.Value
                        local v33 = v_u_6:convert_gameasset_to_assetid(l_Value_0)
                        if v33 == nil then
                            v_u_28:add_set(l_Value_0)
                            v_u_29:add(l_Value_0, p30)
                        else
                            l_Value_0 = v33
                        end;
                        v_u_12:push_back_to(l_Value_0, p30)
                    end;
                end;
            end;
            for _, v34 in p_u_9:key_itr() do
                f_r_find_spdecals(v34)
            end;
            if v_u_4:is_dev_build() then
                local v35 = v_u_28:key_list()
                table.sort(v35:get_table())
                for _, v36 in v35:key_itr() do
                    v_u_1:warnf("UNHANDLEDSPDECAL-%s[%s]", v36, v_u_29:get(v36):GetFullName())
                end;
            end;
            for v37, _ in v_u_12:key_itr() do
                if v_u_4:is_mobile() then
                    if v_u_6.Priority1:contains(v37) then
                        v_u_13:push_back(v37)
                    end;
                else
                    v_u_13:push_back(v37)
                end;
            end;
            v_u_13:sort(function(p38, p39) --[[ Line: 212 ]]
                --[[ Upvalues: (ref 1): v_u_6 ]]
                return (v_u_6.Priority1:contains(p39) and 1 or (v_u_6.Priority2:contains(p39) and 2 or 3)) - (v_u_6.Priority1:contains(p38) and 1 or (v_u_6.Priority2:contains(p38) and 2 or 3));
            end)
        end;
        v11.set_should_load = function(_, p40) --[[ Name: set_should_load ]] --[[ Line: 229 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): l_RequestQueueSize_0, (ref 3): s_ContentProvider_0 ]]
            v_u_15 = p40
            if v_u_15 then
                l_RequestQueueSize_0 = s_ContentProvider_0.RequestQueueSize
            end;
        end;
        local v_u_41 = 0
        v11.update = function(_, p42, p43) --[[ Name: update ]] --[[ Line: 237 ]]
            --[[ Upvalues: (copy 1): f_update_loading_display, (ref 2): v_u_15, (copy 3): p_u_10, (copy 4): v_u_13, (ref 5): v_u_14, (copy 6): l_ImageLabel_0, (ref 7): v_u_41, (ref 8): s_ContentProvider_0, (copy 9): v_u_12 ]]
            f_update_loading_display(p42, p43)
            if v_u_15 == false then
                return;
            elseif p_u_10:count() > 0 then
                return;
            elseif v_u_13:count() ~= 0 then
                local v_u_44 = v_u_13:get(1)
                if v_u_14 ~= v_u_44 then
                    v_u_14 = v_u_44
                    l_ImageLabel_0.Image = v_u_44
                    v_u_41 = 0
                    spawn(function() --[[ Line: 250 ]]
                        --[[ Upvalues: (ref 1): s_ContentProvider_0, (ref 2): l_ImageLabel_0, (ref 3): v_u_13, (ref 4): v_u_12, (copy 5): v_u_44 ]]
                        s_ContentProvider_0:PreloadAsync({ l_ImageLabel_0 })
                        v_u_13:pop_front()
                        local v45 = v_u_12:list_of(v_u_44)
                        for v46 = 1, v45:count() do
                            local v47 = v45:get(v46)
                            if v47.ClassName == "Decal" or v47.ClassName == "Texture" then
                                v47.Texture = v_u_44
                            end;
                            if v47.ClassName == "ImageLabel" then
                                v47.Image = v_u_44
                            end;
                            if v47.ClassName == "MeshPart" then
                                v47.TextureID = v_u_44
                            end;
                        end;
                        v45:clear()
                    end)
                end;
                v_u_41 = v_u_41 + 1
            end;
        end;
        f_cons()
        return v11;
    end
};
